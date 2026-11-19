/**
 * 生成一个 2×2×2 的测试立方体 GLB（约 1KB）。
 * 作用：不依赖任何建模软件，立刻验证「小程序能否加载 GLB」这条链路。
 * 用法：node make-cube-glb.mjs
 */
import { writeFileSync, mkdirSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const OUT = resolve(__dirname, '../assets/glb/cube.glb')

const S = 1 // 半边长 → 模型尺寸 2×2×2

// 6 个面，每面 4 个顶点，法线朝外
const FACES = [
  { n: [1, 0, 0], v: [[S, -S, S], [S, -S, -S], [S, S, -S], [S, S, S]] },
  { n: [-1, 0, 0], v: [[-S, -S, -S], [-S, -S, S], [-S, S, S], [-S, S, -S]] },
  { n: [0, 1, 0], v: [[-S, S, S], [S, S, S], [S, S, -S], [-S, S, -S]] },
  { n: [0, -1, 0], v: [[-S, -S, -S], [S, -S, -S], [S, -S, S], [-S, -S, S]] },
  { n: [0, 0, 1], v: [[-S, -S, S], [S, -S, S], [S, S, S], [-S, S, S]] },
  { n: [0, 0, -1], v: [[S, -S, -S], [-S, -S, -S], [-S, S, -S], [S, S, -S]] }
]

const positions = []
const normals = []
const indices = []

let base = 0
for (const face of FACES) {
  for (const p of face.v) {
    positions.push(...p)
    normals.push(...face.n)
  }
  indices.push(base, base + 1, base + 2, base, base + 2, base + 3)
  base += 4
}

// ---- 组装二进制缓冲 ----
const posBuf = Buffer.alloc(positions.length * 4)
positions.forEach((v, i) => posBuf.writeFloatLE(v, i * 4))

const normBuf = Buffer.alloc(normals.length * 4)
normals.forEach((v, i) => normBuf.writeFloatLE(v, i * 4))

const idxBuf = Buffer.alloc(indices.length * 2)
indices.forEach((v, i) => idxBuf.writeUInt16LE(v, i * 2))

const bin = Buffer.concat([posBuf, normBuf, idxBuf])

const gltf = {
  asset: { version: '2.0', generator: 'make-cube-glb.mjs' },
  scene: 0,
  scenes: [{ nodes: [0] }],
  nodes: [{ name: 'Cube', mesh: 0 }],
  meshes: [
    {
      name: 'Cube',
      primitives: [
        { attributes: { POSITION: 0, NORMAL: 1 }, indices: 2, material: 0 }
      ]
    }
  ],
  materials: [
    {
      name: 'CubeMat',
      doubleSided: true,
      pbrMetallicRoughness: {
        baseColorFactor: [0.35, 0.62, 0.92, 1],
        metallicFactor: 0.15,
        roughnessFactor: 0.55
      }
    }
  ],
  accessors: [
    {
      bufferView: 0,
      componentType: 5126,
      count: positions.length / 3,
      type: 'VEC3',
      min: [-S, -S, -S],
      max: [S, S, S]
    },
    { bufferView: 1, componentType: 5126, count: normals.length / 3, type: 'VEC3' },
    { bufferView: 2, componentType: 5123, count: indices.length, type: 'SCALAR' }
  ],
  bufferViews: [
    { buffer: 0, byteOffset: 0, byteLength: posBuf.length, target: 34962 },
    { buffer: 0, byteOffset: posBuf.length, byteLength: normBuf.length, target: 34962 },
    {
      buffer: 0,
      byteOffset: posBuf.length + normBuf.length,
      byteLength: idxBuf.length,
      target: 34963
    }
  ],
  buffers: [{ byteLength: bin.length }]
}

// ---- 打包成 GLB ----
let jsonBuf = Buffer.from(JSON.stringify(gltf), 'utf8')
const jsonPad = (4 - (jsonBuf.length % 4)) % 4
if (jsonPad) jsonBuf = Buffer.concat([jsonBuf, Buffer.alloc(jsonPad, 0x20)])

const binPad = (4 - (bin.length % 4)) % 4
const binBuf = binPad ? Buffer.concat([bin, Buffer.alloc(binPad, 0)]) : bin

const total = 12 + 8 + jsonBuf.length + 8 + binBuf.length

const header = Buffer.alloc(12)
header.writeUInt32LE(0x46546c67, 0) // magic 'glTF'
header.writeUInt32LE(2, 4) // version
header.writeUInt32LE(total, 8) // total length

const jsonHeader = Buffer.alloc(8)
jsonHeader.writeUInt32LE(jsonBuf.length, 0)
jsonHeader.writeUInt32LE(0x4e4f534a, 4) // 'JSON'

const binHeader = Buffer.alloc(8)
binHeader.writeUInt32LE(binBuf.length, 0)
binHeader.writeUInt32LE(0x004e4942, 4) // 'BIN\0'

const glb = Buffer.concat([header, jsonHeader, jsonBuf, binHeader, binBuf])

mkdirSync(dirname(OUT), { recursive: true })
writeFileSync(OUT, glb)

console.log(`✅ 已生成 ${OUT}`)
console.log(`   大小 ${glb.length} 字节，${positions.length / 3} 个顶点，${indices.length / 3} 个三角面`)
