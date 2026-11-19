#!/usr/bin/env node
/**
 * GLB 预检脚本
 *
 * 扫描目录下的 .glb 文件，校验：
 *   1. 文件头（glTF magic + version 2 + 声明长度与实际一致）
 *   2. 文件大小（超过 8MB 拒绝）
 *   3. 是否依赖 XR-FRAME 不支持的压缩扩展（Draco / meshopt）
 *   4. 统计顶点数 / 三角面数 / 最大贴图尺寸
 *
 * 输出：
 *   - models.generated.json   仅含通过校验的模型
 *   - 控制台报告              通过 / 拒绝 及原因
 *
 * 用法：
 *   node precheck.mjs                         扫描 ../cloud-upload/models
 *   node precheck.mjs --dir <目录> --base <URL> --out <输出文件>
 */
import { readFileSync, readdirSync, writeFileSync, existsSync, statSync } from 'node:fs'
import { join, resolve, extname, basename, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'
import { NodeIO } from '@gltf-transform/core'

const __dirname = dirname(fileURLToPath(import.meta.url))

const GLB_MAGIC = 0x46546c67 // 'glTF'
const MAX_BYTES = 8 * 1024 * 1024
const UNSUPPORTED_EXT = ['KHR_draco_mesh_compression', 'EXT_meshopt_compression']

// ---------- 参数解析 ----------
function parseArgs(argv) {
  const args = { dir: '../cloud-upload/models', base: '', out: '../cloud-upload/models.generated.json' }
  for (let i = 0; i < argv.length; i += 2) {
    const k = argv[i]
    const v = argv[i + 1]
    if (k === '--dir') args.dir = v
    else if (k === '--base') args.base = v
    else if (k === '--out') args.out = v
  }
  return args
}

// ---------- 工具函数 ----------
function readGlbHeader(buf) {
  if (buf.length < 12) return { ok: false, reason: '文件小于 12 字节' }

  const magic = buf.readUInt32LE(0)
  const version = buf.readUInt32LE(4)
  const declared = buf.readUInt32LE(8)

  if (magic !== GLB_MAGIC) return { ok: false, reason: '文件头不是 glTF（可能不是 GLB）' }
  if (version !== 2) return { ok: false, reason: `不支持的 glTF 版本：${version}` }
  if (declared !== buf.length) {
    return { ok: false, reason: `头部声明长度 ${declared} 与实际 ${buf.length} 不一致` }
  }
  return { ok: true }
}

function toSlug(name) {
  return name
    .toLowerCase()
    .replace(/\.[^.]+$/, '')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
}

function formatSize(bytes) {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / 1024 / 1024).toFixed(2) + ' MB'
}

// ---------- 主流程 ----------
async function main() {
  const args = parseArgs(process.argv.slice(2))
  const dir = resolve(__dirname, args.dir)
  const outPath = resolve(__dirname, args.out)

  if (!existsSync(dir)) {
    console.error(`❌ 目录不存在：${dir}`)
    process.exit(1)
  }

  const files = readdirSync(dir).filter((f) => extname(f).toLowerCase() === '.glb')
  if (!files.length) {
    console.error(`❌ ${dir} 下没有 .glb 文件`)
    process.exit(1)
  }

  const io = new NodeIO()
  const passed = []
  const rejected = []

  console.log(`\n扫描目录：${dir}`)
  console.log(`发现 ${files.length} 个 GLB 文件\n`)
  console.log('─'.repeat(78))

  for (const file of files) {
    const full = join(dir, file)
    const size = statSync(full).size
    const buf = readFileSync(full)

    // 1. 文件头
    const header = readGlbHeader(buf)
    if (!header.ok) {
      rejected.push({ file, reason: header.reason })
      console.log(`❌ ${file}\n   原因：${header.reason}`)
      continue
    }

    // 2. 体积
    if (size > MAX_BYTES) {
      rejected.push({ file, reason: `超过 8MB 上限（${formatSize(size)}）` })
      console.log(`❌ ${file}\n   原因：体积 ${formatSize(size)} 超过 8MB`)
      continue
    }

    // 3. 解析并用扩展校验
    let doc
    try {
      doc = await io.read(full)
    } catch (err) {
      rejected.push({ file, reason: `解析失败：${err.message}` })
      console.log(`❌ ${file}\n   原因：解析失败 ${err.message}`)
      continue
    }

    const root = doc.getRoot()
    const used = root.listExtensionsUsed().map((e) => e.extensionName)
    const bad = used.filter((e) => UNSUPPORTED_EXT.includes(e))
    if (bad.length) {
      rejected.push({ file, reason: `依赖 XR-FRAME 不支持的扩展：${bad.join(', ')}` })
      console.log(`❌ ${file}\n   原因：依赖不支持扩展 ${bad.join(', ')}`)
      continue
    }

    // 4. 统计
    let vertices = 0
    let triangles = 0
    for (const mesh of root.listMeshes()) {
      for (const prim of mesh.listPrimitives()) {
        const pos = prim.getAttribute('POSITION')
        if (pos) vertices += pos.getCount()
        const idx = prim.getIndices()
        if (idx) triangles += idx.getCount() / 3
        else if (pos) triangles += pos.getCount() / 3
      }
    }

    const textures = root.listTextures().map((t) => t.getSize()).filter((s) => s && s[0] > 0)
    const maxTexture = textures.length ? Math.max(...textures.map((s) => s[0])) : 0

    const id = toSlug(file)
    const entry = {
      id,
      name: basename(file, extname(file)),
      source: '待补充',
      url: args.base ? `${args.base.replace(/\/$/, '')}/${file}` : `/${file}`,
      sizeBytes: size,
      sizeText: formatSize(size),
      thumbnail: '',
      note: '',
      stats: {
        vertices: Math.round(vertices),
        triangles: Math.round(triangles),
        maxTextureSize: maxTexture
      }
    }

    passed.push(entry)
    console.log(
      `✅ ${file}\n   ${formatSize(size)} · ${entry.stats.triangles} 面 · ` +
        `${entry.stats.vertices} 顶点 · 贴图 ${maxTexture || '-'}px`
    )
  }

  console.log('─'.repeat(78))
  console.log(`\n通过 ${passed.length} 个，拒绝 ${rejected.length} 个`)

  if (rejected.length) {
    console.log('\n被拒绝的文件：')
    rejected.forEach((r) => console.log(`  · ${r.file} —— ${r.reason}`))
  }

  // 只在有通过项时写文件，避免把清单写成空的
  if (passed.length) {
    const out = { version: 1, updatedAt: new Date().toISOString().slice(0, 10), models: passed }
    writeFileSync(outPath, JSON.stringify(out, null, 2) + '\n', 'utf8')
    console.log(`\n✅ 已写入 ${outPath}`)
    console.log('   检查无误后重命名为 models.json 上传到 COS\n')
  } else {
    console.log('\n⚠️ 没有任何模型通过校验，未写入文件\n')
  }

  process.exit(rejected.length ? 2 : 0)
}

main().catch((err) => {
  console.error('脚本异常：', err)
  process.exit(1)
})
