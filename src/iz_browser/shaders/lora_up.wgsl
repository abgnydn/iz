// LoRA UP PROJECTION — y += temp @ B.T (additive into base output)
//
// Computes: output[m] += scale * sum_r temp[r] * B[m, r]
//   for m in [0, M)
//
// Part 2 of LoRA adaptation. Reads the `temp` vector produced by
// lora_down.wgsl and the existing `output` buffer (already holds
// the int4 base matmul result), writes the updated output in-place.
//
// The `scale` uniform bakes LoRA's alpha/rank factor at dispatch time,
// so B on disk is stored un-scaled.
//
// One thread = one output element. workgroup_size(64), @dispatch M/64 wgs.
//
// Bindings:
//   @binding(0): output  array<f16>  (read_write) — y [M] (read-modify-write)
//   @binding(1): temp    array<f16>  (read)       — [RANK]
//   @binding(2): B       array<f16>  (read)       — LoRA B weights [M, RANK] row-major
//   @binding(3): args    uniform     — { RANK, M, scale }

enable f16;

@group(0) @binding(0) var<storage, read_write> output_buf : array<f16>;
@group(0) @binding(1) var<storage, read> temp_buf : array<f16>;
@group(0) @binding(2) var<storage, read> B_buf : array<f16>;

struct LoRAUpArgs {
  RANK: u32,   // e.g. 16
  M:    u32,   // output dim (e.g. 9216 for qkv, 3072 for oProj)
  scale: f32,  // alpha / rank, baked at dispatch time
  _pad: u32,
}
@group(0) @binding(3) var<uniform> args : LoRAUpArgs;

@compute @workgroup_size(64, 1, 1)
fn lora_up(
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

  let current : f32 = f32(output_buf[m]);
  output_buf[m] = f16(current + args.scale * acc);
}
