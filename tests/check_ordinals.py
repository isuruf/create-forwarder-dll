"""Check that a forwarder DLL keeps the export ordinals of the DLL it forwards to.

Usage: python check_ordinals.py <input.dll> <forwarder.dll>

Regression test for https://github.com/conda-forge/openmp-feedstock/issues/236
where binaries importing libiomp5md.dll by ordinal failed to load with
ERROR_INVALID_ORDINAL because the forwarder renumbered the exports.
"""
import ctypes
import os
import struct
import sys


def read_exports(path):
  """Return a dict mapping exported names to ordinals by parsing the PE export table."""
  with open(path, "rb") as f:
    data = f.read()

  pe = struct.unpack_from("<I", data, 0x3c)[0]
  assert data[pe:pe + 4] == b"PE\0\0", f"{path} is not a PE file"
  num_sections = struct.unpack_from("<H", data, pe + 6)[0]
  opt_header_size = struct.unpack_from("<H", data, pe + 20)[0]
  opt_header = pe + 24
  magic = struct.unpack_from("<H", data, opt_header)[0]
  data_dirs = opt_header + (96 if magic == 0x10b else 112)
  export_rva, export_size = struct.unpack_from("<II", data, data_dirs)
  if export_size == 0:
    return {}

  sections = []
  for i in range(num_sections):
    vsize, va, raw_size, raw_ptr = struct.unpack_from("<IIII", data, opt_header + opt_header_size + 40 * i + 8)
    sections.append((va, max(vsize, raw_size), raw_ptr))

  def offset(rva):
    for va, size, raw_ptr in sections:
      if va <= rva < va + size:
        return rva - va + raw_ptr
    raise ValueError(f"RVA {rva:#x} not in any section of {path}")

  base, _, num_names, _, names_rva, ordinals_rva = struct.unpack_from("<IIIIII", data, offset(export_rva) + 16)
  exports = {}
  for i in range(num_names):
    name_off = offset(struct.unpack_from("<I", data, offset(names_rva) + 4 * i)[0])
    name = data[name_off:data.index(b"\0", name_off)].decode("ascii")
    exports[name] = base + struct.unpack_from("<H", data, offset(ordinals_rva) + 2 * i)[0]
  return exports


def main():
  input_dll, forwarder_dll = sys.argv[1:]
  expected = read_exports(input_dll)
  actual = read_exports(forwarder_dll)
  assert expected, f"no exports found in {input_dll}"

  errors = []
  for name, ordinal in sorted(expected.items(), key=lambda x: x[1]):
    if name not in actual:
      errors.append(f"{name}: missing from forwarder")
    elif actual[name] != ordinal:
      errors.append(f"{name}: ordinal {actual[name]} in forwarder, expected {ordinal}")

  if not errors:
    # Resolve every export by ordinal, the way an ordinal-only importer would,
    # and check the forwarder resolves to the same address as the input DLL.
    # Load the input first so the forwarder's target is already in the process.
    os.add_dll_directory(os.path.dirname(os.path.abspath(input_dll)))
    input_lib = ctypes.WinDLL(os.path.abspath(input_dll))
    forwarder_lib = ctypes.WinDLL(os.path.abspath(forwarder_dll))
    for name, ordinal in expected.items():
      try:
        got = ctypes.cast(forwarder_lib[ordinal], ctypes.c_void_p).value
      except AttributeError:
        errors.append(f"{name}: ordinal {ordinal} cannot be resolved in forwarder")
        continue
      want = ctypes.cast(input_lib[ordinal], ctypes.c_void_p).value
      if got != want:
        errors.append(f"{name}: ordinal {ordinal} resolves to {got:#x}, expected {want:#x}")

  if errors:
    print("\n".join(errors))
    sys.exit(f"{len(errors)} ordinal mismatches between {input_dll} and {forwarder_dll}")
  print(f"all {len(expected)} exports of {input_dll} keep their ordinals in {forwarder_dll}")


if __name__ == "__main__":
  main()
