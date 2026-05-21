// LoRA UP PROJECTION (f32 output variant) — y += temp @ B.T, f32 accumulator.
//
// Identical to lora_up.wgsl except the output buffer is f32 instead of f16.
// Used for the LM head, whose int4_matmul_f32 variant writes f32 logits for
// stable argmax/softmax — we must match that precision to not introduce
// rounding before the loss.
//
// Bindings (layout matches lora_up.wgsl):
//   @binding(0): output  array<f32>  (read_write) — y [M] (logits, f32)
//   @binding(1): temp    array<f16>  (read)       — [RANK]
//   @binding(2): B       array<f16>  (read)       — [M, RANK] LoRA up weights
//   @binding(3): args    uniform     — { RANK, M, scale, _ }

enable f16;

@group(0) @binding(0) var<storage, read_write> output_buf : array<f32>;
@group(0) @binding(1) var<storage, read> temp_buf : array<f16>;
@group(0) @binding(2) var<storage, read> B_buf : array<f16>;

struct LoRAUpArgs {
  RANK: u32,
  M:    u32,
  scale: f32,
  _pad: u32,
}
@group(0) @binding(3) var<uniform> args : LoRAUpArgs;

@compute @workgroup_size(64, 1, 1)
fn lora_up_f32(
  @builtin(global_invocation_id) gid : vec3<u32>
) {
  let m : u32 = gid.x;
  if (m >= args.M) { return; }

  let RANK : u32 = args.RANK;
  let row_base : u32 = m * RANK;

  var acc : f32 = 0.0;
  for (var r : u32 = 0u; r < RANK; r = r + 1u) {
    acc = acc + f32(temp_buf[r]) * f32(B_buf[row_base + r]);
  }

  output_buf[m] = output_buf[m] + args.scale * acc;
}
