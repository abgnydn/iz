// LoRA DOWN PROJECTION — x @ A.T
//
// Computes: temp[r] = sum_k input[k] * A[r, k]
//   for r in [0, RANK)
//
// Part 1 of LoRA adaptation. After this dispatch, lora_up.wgsl reads `temp`
// and adds `temp @ B.T` into the existing output buffer produced by
// int4_matmul. Base path stays frozen; only A and B are trainable.
//
// One workgroup = one rank dimension (1 of 16 typically).
// 64 threads cooperatively dot-product over K, then tree-reduce in f32.
//
// Bindings:
//   @binding(0): temp    array<f16>  (read_write) — output [RANK]
//   @binding(1): input   array<f16>  (read)       — x [K]
//   @binding(2): A       array<f16>  (read)       — LoRA A weights [RANK, K] row-major
//   @binding(3): args    uniform     — { K, RANK }

enable f16;

@group(0) @binding(0) var<storage, read_write> temp_buf : array<f16>;
@group(0) @binding(1) var<storage, read> input_buf : array<f16>;
@group(0) @binding(2) var<storage, read> A_buf : array<f16>;

struct LoRAArgs {
  K: u32,     // input dim (e.g. 3072)
  RANK: u32,  // LoRA rank (e.g. 16)
}
@group(0) @binding(3) var<uniform> args : LoRAArgs;

var<workgroup> red_buf : array<f32, 64>;

@compute @workgroup_size(64, 1, 1)
fn lora_down(
  @builtin(workgroup_id) blockIdx : vec3<u32>,
  @builtin(local_invocation_id) threadIdx : vec3<u32>
) {
  let r : u32 = blockIdx.x;
  if (r >= args.RANK) { return; }

  let K : u32 = args.K;
  let tid : u32 = threadIdx.x;
  let row_base : u32 = r * K;

  var acc : f32 = 0.0;
  // Each thread strides by 64 across K
  var k : u32 = tid;
  loop {
    if (k >= K) { break; }
    acc = acc + f32(input_buf[k]) * f32(A_buf[row_base + k]);
    k = k + 64u;
  }

  red_buf[tid] = acc;
  workgroupBarrier();

  if (tid < 32u) { red_buf[tid] = red_buf[tid] + red_buf[tid + 32u]; }
  workgroupBarrier();
  if (tid < 16u) { red_buf[tid] = red_buf[tid] + red_buf[tid + 16u]; }
  workgroupBarrier();
  if (tid < 8u)  { red_buf[tid] = red_buf[tid] + red_buf[tid + 8u]; }
  workgroupBarrier();
  if (tid < 4u)  { red_buf[tid] = red_buf[tid] + red_buf[tid + 4u]; }
  workgroupBarrier();
  if (tid < 2u)  { red_buf[tid] = red_buf[tid] + red_buf[tid + 2u]; }
  workgroupBarrier();
  if (tid < 1u)  { red_buf[tid] = red_buf[tid] + red_buf[tid + 1u]; }
  workgroupBarrier();

  if (tid == 0u) {
    temp_buf[r] = f16(red_buf[0]);
  }
}
