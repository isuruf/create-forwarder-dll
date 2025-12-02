import argparse
import os
import re
import subprocess
import sys

PROCESSOR_ARCHITECTURE = os.environ.get("PROCESSOR_ARCHITECTURE", "")
target_platform = os.environ.get("target_platform", None)

target_platform_map = {
  "win-64": "x64",
  "win-arm64": "ARM64",
  "win-32": "X86",
}

processor_architecture_map = {
  "amd64": "x64",
  "arm64": "ARM64",
  "x86": "X86",
}


def get_compiler():
  from distutils._msvccompiler import MSVCCompiler
  m = MSVCCompiler()
  m.initialize()
  return m


def run(arg):
  return subprocess.check_output(arg, shell=True).decode("utf-8")


def get_machine_default():
  if target_platform and target_platform != "noarch":
    return target_platform_map[target_platform]
  else:
    return processor_architecture_map.get(PROCESSOR_ARCHITECTURE.lower(), "")


def parse_args(args):
  parser = argparse.ArgumentParser(
    prog='create_dll_forwarder',
    description='Create a DLL that forwards to another DLL',
  )
  parser.add_argument('input', help="path to input DLL")
  parser.add_argument('output', help="path to output DLL")
  parser.add_argument('--implementing-dll-name', default=None,
                      help="When the `input` DLL is only the reference for the symbols, but the actual implementation for them is elsewhere")
  parser.add_argument('--machine', default=get_machine_default(),
                      help="machine argument to cl.exe")
  parser.add_argument('--no-temp-dir', action='store_true',
                      help="Do not use a temporary directory to create intermediaries")
  parser.add_argument('--symbol-filter-regex', default=None,
                      help="Only add symbols to forwarder DLL that match this regex")
  return parser.parse_args(args)


def create(input_dll, output_dll, impl_dll, machine, symbol_filter):
  print(f"got input DLL {input_dll}, output DLL {output_dll}" + f", implenting DLL {impl_dll}" * (impl_dll is not None))

  assert input_dll.endswith(".dll")
  input = os.path.basename(input_dll)[:-4]

  assert output_dll.endswith(".dll")
  output = os.path.basename(output_dll)[:-4]

  if impl_dll is not None:
    assert impl_dll.endswith(".dll")
    impl = os.path.basename(impl_dll)[:-4]
  else:
    impl = input

  # create empty object file to which we can attach symbol export list
  open("empty.c", "a").close()
  compiler = get_compiler()
  cl_exe = compiler.cc
  cl_dir = os.path.dirname(cl_exe)
  lib_exe = os.path.join(cl_dir, "lib.exe")
  dumpbin_exe = os.path.join(cl_dir, "dumpbin.exe")

  compiler.spawn([cl_exe, "/c", "empty.c"])

  if symbol_filter is not None:
    print(f"received regex pattern to filter symbols: {symbol_filter!r}")
    symbol_filter = re.compile(symbol_filter)

  # extract symbols from input
  dump = run(f"\"{dumpbin_exe}\" /EXPORTS {input_dll}")
  started = False
  symbols = []
  for line in dump.splitlines():
    if line.strip().startswith("ordinal"):
      started = True
    if line.strip().startswith("Summary"):
      break
    if started and line.strip() != "":
      symbol = line.strip().split(" ")[-1]
      if symbol_filter is not None:
        if symbol_filter.match(symbol):
          symbols.append(symbol)
        else:
          print(f"ignoring: {symbol}")
      else:
        symbols.append(symbol)

  print(f"symbols being added to forwarder DLL:\n{'\n'.join(symbols)}")

  # create def file for explicit symbol export
  with open(f"{input}_impl.def", "w") as f:
    f.write(f"LIBRARY {impl}.dll\n")
    f.write("EXPORTS\n")
    for symbol in symbols:
      f.write(f"  {symbol}\n")

  # create import library with that list of symbols
  compiler.spawn([lib_exe, f"/def:{input}_impl.def", f"/out:{input}_impl.lib", f"/MACHINE:{machine}"])

  # create DLL from empty object and the import library
  with open(f"{output}.def", "w") as f:
    f.write(f"LIBRARY {output}.dll\n")
    f.write("EXPORTS\n")
    for symbol in symbols:
      f.write(f"  {symbol} = {impl}.dll.{symbol}\n")

  compiler.link(
    compiler.SHARED_LIBRARY,
    output_filename=f"{output}.dll",
    extra_preargs=[f"/DEF:{output}.def", f"/MACHINE:{machine}"],
    objects=["empty.obj", f"{input}_impl.lib"]
  )
  run(f"copy {output}.dll {output_dll}")


def main():
  args = parse_args(sys.argv[1:])
  if args.no_temp_dir:
     create(args.input, args.output, args.implementing_dll_name, args.machine, args.symbol_filter_regex)
  else:
     import tempfile
     with tempfile.TemporaryDirectory() as tmpdir:
         os.chdir(tmpdir)
         create(args.input, args.output, args.implementing_dll_name, args.machine, args.symbol_filter_regex)


if __name__ == "__main__":
  main()
