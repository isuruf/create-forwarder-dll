import argparse
import os
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

def run(arg):
  return subprocess.check_output(arg, shell=True).decode("utf-8")


def get_machine_default():
  if target_platform:
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
  parser.add_argument('--machine', default=get_machine_default())
  parser.add_argument('--no-temp-dir', action='store_true')
  return parser.parse_args(args)


def main(args):
  input_dll = args.input
  input_dir = os.path.dirname(args.input)
  assert input_dll.endswith(".dll")
  input = os.path.basename(input_dll)[:-4]

  output_dll = args.output
  output_dir = os.path.dirname(args.output)
  assert output_dll.endswith(".dll")
  output = os.path.basename(output_dll)[:-4]
  
  # create empty object file to which we can attach symbol export list
  open("empty.c", "a").close()
  run("cl.exe /c empty.c")

  # extract symbols from input
  dump = run(f"dumpbin /EXPORTS {input_dll}")
  started = False
  symbols = []
  for line in dump.splitlines():
    if line.strip().startswith("ordinal"):
      started = True
    if line.strip().startswith("Summary"):
      break 
    if started and line.strip() != "":
      symbol = line.strip().split(" ")[-1]
      symbols.append(symbol)

  # create def file for explicit symbol export
  with open(f"{input}.def", "w") as f:
    f.write(f"LIBRARY {input}.dll\n")
    f.write("EXPORTS\n")
    for symbol in symbols:
      f.write(f"  {symbol}\n")
      
  # create import library with that list of symbols
  run(f"lib /def:{input}.def /out:{input}.lib /MACHINE:{args.machine}")
  
  # create DLL from empty object and the import library
  with open(f"{output}.def", "w") as f:
    f.write(f"LIBRARY {output}.dll\n")
    f.write("EXPORTS\n")
    for symbol in symbols:
      f.write(f"  {symbol} = {input}.{symbol}\n")

  cl_exe = run("where cl.exe")
  link_exe = os.path.join(os.path.dirname(cl_exe), "link.exe")
  run(f"\"{link_exe}\" /DLL /OUT:{output}.dll /DEF:{output}.def /MACHINE:{args.machine} empty.obj {input}.lib")
  run(f"copy {output}.dll {output_dll}")

if __name__ == "__main__":
  args = parse_args(sys.argv[1:])
  if args.no_temp_dir:
     main(args)
  else:
     import tempfile
     with tempfile.TemporaryDirectory() as tmpdir:
         os.chdir(tmpdir)
         main(args)
