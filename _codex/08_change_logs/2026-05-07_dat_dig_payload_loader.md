# DAT DIG payload loader

## What changed
- DAT loader now distinguishes channel files referenced by header field `211`.
- `.chn` files keep the existing internal data-offset behavior.
- `.dig` files are treated as raw binary payload files and are read from byte offset `0`.
- Loader metadata now records channel file kind, resolved data offset, and dtype:
  - `dat_channel_file_type_map`
  - `dat_channel_data_offset_map`
  - `dat_channel_dtype_map`

## Why
- DD8x/DAT exports can reference digital contact channels through `.dig` files.
- Sample `.dig` files contain exactly `220 * dtype.itemsize` bytes and no CHN-style header.
- Treating `.dig` like `.chn` caused the loader to fall back to header `221=1`, reading REAL64 samples one byte off and producing denormal near-zero values.

## Data policy
- No raw sample values are rewritten or thresholded.
- The loader only changes how the referenced binary payload is located before applying DAT header `240` offset and `241` scale.
- Existing DAT `215` no-value header handling remains metadata-only.

## Risk
- DAT import behavior changes for `.dig` channels only.
- Other non-`.chn` referenced files are not guessed unless their file size exactly matches `220 * dtype.itemsize`, in which case they are read as raw payload and tagged in metadata.
