#!/usr/bin/env node
import { copyFile, mkdir, readdir, rm } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HELP = `
Mix MP3 files into many output folders.

Usage:
  bun src/cli.js --input <mp3-folder> --output <output-folder> --folders <count> [options]

Options:
  -i, --input <path>       Folder containing source .mp3 files
  -o, --output <path>      Folder where output folders are created
  -n, --folders <count>    Number of folders to create
  --prefix / --no-prefix   Add order prefix to file names, default: --prefix
  --clean                  Delete output folder before generating
  --seed <text>            Deterministic shuffle seed
  -h, --help               Show help

Example:
  bun src/cli.js --input "D:\\music\\source" --output "D:\\music\\mixed" --folders 50 --clean
  bun src/cli.js --input ./source --output ./mixed --folders 50 --seed batch-1
`;

function parseArgs(argv) {
  const options = {
    prefix: true,
    clean: false,
    seed: undefined,
  };

  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    const next = argv[index + 1];

    if (arg === '-h' || arg === '--help') {
      options.help = true;
    } else if (arg === '-i' || arg === '--input') {
      options.input = readValue(arg, next);
      index += 1;
    } else if (arg === '-o' || arg === '--output') {
      options.output = readValue(arg, next);
      index += 1;
    } else if (arg === '-n' || arg === '--folders') {
      options.folders = Number.parseInt(readValue(arg, next), 10);
      index += 1;
    } else if (arg === '--prefix') {
      options.prefix = true;
    } else if (arg === '--no-prefix') {
      options.prefix = false;
    } else if (arg === '--clean') {
      options.clean = true;
    } else if (arg === '--seed') {
      options.seed = readValue(arg, next);
      index += 1;
    } else {
      throw new Error(`Unknown option: ${arg}`);
    }
  }

  return options;
}

function readValue(option, value) {
  if (!value || value.startsWith('-')) {
    throw new Error(`Missing value for ${option}`);
  }

  return value;
}

function validateOptions(options) {
  if (options.help) {
    return;
  }

  if (!options.input) {
    throw new Error('Missing required option: --input');
  }

  if (!options.output) {
    throw new Error('Missing required option: --output');
  }

  if (!Number.isInteger(options.folders) || options.folders < 1) {
    throw new Error('--folders must be a positive integer');
  }
}

async function getMp3Files(inputFolder) {
  const entries = await readdir(inputFolder, { withFileTypes: true });
  const files = entries
    .filter((entry) => entry.isFile() && path.extname(entry.name).toLowerCase() === '.mp3')
    .map((entry) => entry.name)
    .sort((left, right) => left.localeCompare(right, undefined, { numeric: true }));

  if (files.length === 0) {
    throw new Error(`No .mp3 files found in ${inputFolder}`);
  }

  return files;
}

function createRandom(seedText) {
  if (!seedText) {
    return Math.random;
  }

  let state = 2166136261;
  for (const char of seedText) {
    state ^= char.codePointAt(0);
    state = Math.imul(state, 16777619);
  }

  return () => {
    state += 0x6D2B79F5;
    let value = state;
    value = Math.imul(value ^ (value >>> 15), value | 1);
    value ^= value + Math.imul(value ^ (value >>> 7), value | 61);
    return ((value ^ (value >>> 14)) >>> 0) / 4294967296;
  };
}

function shuffleFiles(files, random) {
  const shuffled = [...files];

  for (let index = shuffled.length - 1; index > 0; index -= 1) {
    const targetIndex = Math.floor(random() * (index + 1));
    [shuffled[index], shuffled[targetIndex]] = [shuffled[targetIndex], shuffled[index]];
  }

  return shuffled;
}

function prefixName(index, fileName, totalFiles) {
  const width = String(totalFiles).length;
  const order = String(index + 1).padStart(width, '0');
  return `${order}_${fileName}`;
}

async function generateFolders(options) {
  const inputFolder = path.resolve(options.input);
  const outputFolder = path.resolve(options.output);
  const files = await getMp3Files(inputFolder);
  const random = createRandom(options.seed);

  if (options.clean) {
    await rm(outputFolder, { recursive: true, force: true });
  }

  await mkdir(outputFolder, { recursive: true });

  for (let folderIndex = 0; folderIndex < options.folders; folderIndex += 1) {
    const folderName = String(folderIndex + 1).padStart(String(options.folders).length, '0');
    const targetFolder = path.join(outputFolder, folderName);
    const shuffledFiles = shuffleFiles(files, random);

    await mkdir(targetFolder, { recursive: true });

    for (let fileIndex = 0; fileIndex < shuffledFiles.length; fileIndex += 1) {
      const fileName = shuffledFiles[fileIndex];
      const targetName = options.prefix ? prefixName(fileIndex, fileName, shuffledFiles.length) : fileName;
      await copyFile(path.join(inputFolder, fileName), path.join(targetFolder, targetName));
    }
  }

  return {
    inputFolder,
    outputFolder,
    sourceFiles: files.length,
    folders: options.folders,
  };
}

async function main() {
  try {
    const options = parseArgs(process.argv.slice(2));
    validateOptions(options);

    if (options.help) {
      console.log(HELP.trim());
      return;
    }

    const result = await generateFolders(options);
    console.log(`Done: created ${result.folders} folders from ${result.sourceFiles} MP3 files.`);
    console.log(`Input: ${result.inputFolder}`);
    console.log(`Output: ${result.outputFolder}`);
  } catch (error) {
    console.error(`Error: ${error.message}`);
    console.error('Run with --help for usage.');
    process.exitCode = 1;
  }
}

const isDirectRun = process.argv[1] && fileURLToPath(import.meta.url) === path.resolve(process.argv[1]);

if (isDirectRun) {
  await main();
}

export { generateFolders, parseArgs, shuffleFiles };
