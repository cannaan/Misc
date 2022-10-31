import sys
import subprocess
import re
import os
import argparse
import platform

def DefaultHubInstallPath():
	if platform.system() == 'Windows':
		return 'C:/Program Files/Unity/Hub/Editor'
	if platform.system() == 'Darwin':
		return '/Applications/Unity/Hub/Editor'

def DefaultNDKPath(hubInstallPath, unityVersion):
	if hubInstallPath == None:
		hubInstallPath = DefaultHubInstallPath()
	if hubInstallPath == None:
		return None

	unityInstallPath = os.path.join(hubInstallPath, unityVersion)
	ndkPath = None
	if platform.system() == 'Windows':
		ndkPath = os.path.join(unityInstallPath, 'Editor/Data/PlaybackEngines/AndroidPlayer/NDK')
	if platform.system == 'Darwin':
			ndkPath = os.path.join(unityInstallPath, 'PlaybackEngines/AndroidPlayer/NDK')
	if os.path.isdir(ndkPath):
		return ndkPath

def ReadUnityVersion(lines):
	pattern = re.compile(r"Version\s?'(?P<UnityVersion>\d\d\d\d\.\d\.\d+[fab]\d+)\s?\([0-9a-f]+\)'")
	for l in lines:
		match = pattern.search(l)
		if match != None:
			return match.group("UnityVersion")

def ReadArchitechture(lines):
	pattern = re.compile(r"CPU\s?'(?P<Arch>arm64-v8a|armeabi-v7a|x86|x64)'")
	for l in lines:
		match = pattern.search(l)
		if match != None:
			return match.group("Arch")

def GetAddr2lineToolPath(ndkPath, arch):
	toolname = None
	if arch == 'arm64-v8a':
		toolname = 'aarch64-linux-android-addr2line'
	elif arch == 'armeabi-v7a': 
		toolname = 'arm-linux-androideabi-addr2line'
	elif arch == 'x86':
		toolname = 'i686-linux-android-addr2line'
	elif arch == 'x86_64':
		toolname = 'x86_64-linux-android-addr2line'
	if toolname != None:
		if platform.system() == 'Windows':
			return os.path.join(ndkPath, 'toolchains/llvm/prebuilt/windows-x86_64/bin/' + toolname + '.exe')
		elif platform.system() == 'Darwin':
			return os.path.join(ndkPath, 'toolchains/llvm/prebuilt/darwin-x86_64/bin/' + toolname)



parser = argparse.ArgumentParser(description = "addr2line for Unity android")
parser.add_argument('tracebackfile')
parser.add_argument('-u', '--unity', required = False, metavar = 'UnityVersion', help = 'Used to locate NDK path to UnityHubInstallPath/Editor/UnityVersion/PlaybackEngines/AndroidPlayer/NDK. If -k/--ndk is specified, this is not necessary.')
parser.add_argument('-k', '--ndk', required = False, metavar = 'NDKPath')
parser.add_argument('-a', '--arch', required = False, metavar = 'archetcture', help = 'armeabi-v7a arm64-v8a x86 x64')
parser.add_argument('--hub', required = False, metavar = "UnityHubInstallPath")
parser.add_argument('-s', '--symbol', required = True, metavar = 'symbolFilePath')

args = parser.parse_args()
if args == None:
	exit(1)

addrFile = open(args.tracebackfile, 'rt')
lines = addrFile.readlines()

unityVersion = args.unity
if unityVersion == None:
	unityVersion = ReadUnityVersion(lines)

architechture = args.arch
if architechture == None:
	architechture = ReadArchitechture(lines)

ndkPath = args.ndk
if ndkPath == None and unityVersion != None:
	ndkPath = DefaultNDKPath(args.hub, unityVersion)

if ndkPath == None:
	print("can not locate NDK")
	exit(1)

if architechture == None:
	print("can not determine architechture")
	exit(1)

toolPath = GetAddr2lineToolPath(ndkPath, architechture)
if toolPath == None:
	print("can not find addr2lines tool")
	exit(1)

symbolsPath = args.symbol

def GetSymbolFilePath(lib):
	path = os.path.join(symbolsPath, lib)
	if os.path.isfile(path):
		return path
	path = os.path.join(symbolsPath, os.path.join(architechture, lib))
	if os.path.isfile(path):
		return path

def addr2line(addr, libName):
	libPath = GetSymbolFilePath(libName)
	if libPath != None:
		process = subprocess.Popen('\"' + toolPath + '\"' + " -Cpife " + libPath + " " + addr, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		out, err = process.communicate()
		if err.decode('ascii') != '':
			print(err)
		return out.decode('ascii').rstrip()

def parseLine(originline):
	pattern = re.compile(r"#\d+\s+pc\s+(?P<addr>(0x)?[0-9a-f]+)\s+.*(?P<lib>lib\w+\.so)")
	match = pattern.search(originline)
	if match != None:
		line = addr2line(match.group('addr'), match.group('lib'))
		if line != None and line != '':
			return originline.replace(match.group('addr'), line)
	return originline

for l in lines:
	print(parseLine(l).rstrip())
