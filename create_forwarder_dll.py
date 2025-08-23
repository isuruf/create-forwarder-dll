import argparse
import os
import subprocess
import sys

PROCESSOR_ARCHITECTURE = os.environ.get("PROCESSOR_ARCHITECTURE", "")

def run(arg):
  return subprocess.check_output(arg, shell=True).decode("utf-8")

def main(args):
  parser = argparse.ArgumentParser(
    prog='create_dll_forwarder',
    description='Create a DLL that forwards to another DLL',
  )
  parser.add_argument('input', help="path to input DLL")
  parser.add_argument('output', help="path to output DLL")
  parser.add_argument('--arch', default=PROCESSOR_ARCHITECTURE)

  args = parser.parse_args(args)

  input_dir = os.path.dirname(args.input)
  input_dll = os.path.basename(args.input)
  assert input_dll.endswith(".dll")
  input = input_dll[:-4]

  output_dir = os.path.dirname(args.output)
  output_dll = os.path.basename(args.output)
  assert output_dll.endswith(".dll")
  output = output_dll[:-4]
  
  if args.arch.lower() == "amd64":
    machine = "x64"
  elif args.arch.lower() == "arm64":
    machine = "ARM64"
  elif args.arch.lower() == "x86":
    machine = "X86"
  else:
    raise NotImplementedError(f"Unknown arch")
  
  # create empty object file to which we can attach symbol export list
  open("empty.c", "a").close()
  run("cl.exe /c empty.c")

  # extract symbols from input
  dump = run(f"dumpbin /EXPORTS {input_dir}/{input_dll}")
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
  run(f"lib /def:{input}.def /out:{input}.lib /MACHINE:{machine}")
  
  # create DLL from empty object and the import library
  with open(f"{output}.def", "w") as f:
    f.write(f"LIBRARY {output}.dll\n")
    f.write("EXPORTS\n")
    for symbol in symbols:
      f.write(f"  {symbol} = {input}.{symbol}\n")

  run(f"link.exe /DLL /OUT:{output}.dll /DEF:{output}.def /MACHINE:{machine} empty.obj {input}.lib")
  run(f"copy {output}.dll {output_dir}/{output_dll}")

if __name__ == "__main__":
  import tempfile
  with tempfile.TemporaryDirectory() as tmpdir:
     os.chdir(tmpdir)
     main(sys.argv[1:])
