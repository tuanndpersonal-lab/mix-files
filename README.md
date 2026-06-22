# Mix Files

CLI/executable tool to create many output folders from one source folder of MP3 files. Each output folder receives all MP3 files in a shuffled order. By default, files are renamed with order prefixes such as `1_song.mp3`, `2_track.mp3` so the playback order is clear.

## Download Executable

Download the latest release from GitHub:

- Windows: `mix-files-windows.exe`
- macOS: `mix-files-macos`

Run the executable with no arguments and it will ask for:

1. Source MP3 folder path
2. Output folder path
3. Number of folders to create
4. Whether to clean the output folder first
5. Whether to add order prefixes

On macOS, if needed, allow execution once:

```bash
chmod +x ./mix-files-macos
./mix-files-macos
```

## Requirements

- Bun installed on macOS or Windows: https://bun.sh
- A source folder containing `.mp3` files

If you use the release executable, Bun is not required.

No `ffmpeg` is required because this tool shuffles and copies files; it does not merge audio tracks into one MP3.

## Usage

```bash
bun src/cli.js --input <source-folder> --output <output-folder> --folders <count>
```

### Windows example

```powershell
bun src/cli.js --input "D:\music\source" --output "D:\music\mixed" --folders 50 --clean
```

### macOS example

```bash
bun src/cli.js --input "/Users/me/Music/source" --output "/Users/me/Music/mixed" --folders 50 --clean
```

## Options

- `--input`, `-i`: Source folder containing `.mp3` files.
- `--output`, `-o`: Output folder where generated folders are created.
- `--folders`, `-n`: Number of folders to create.
- `--prefix`: Add order prefixes to copied file names. This is enabled by default.
- `--no-prefix`: Keep original file names.
- `--clean`: Delete the output folder before generating new folders.
- `--seed <text>`: Use a deterministic shuffle seed so the same command creates the same result.
- `--help`, `-h`: Show help.

## Output Structure

If you run:

```bash
bun src/cli.js --input ./source --output ./mixed --folders 3 --clean
```

The output looks like:

```text
mixed/
  1/
    01_song-c.mp3
    02_song-a.mp3
    03_song-b.mp3
  2/
    01_song-b.mp3
    02_song-c.mp3
    03_song-a.mp3
  3/
    01_song-a.mp3
    02_song-b.mp3
    03_song-c.mp3
```

Folder names are zero-padded when needed, for example `01` to `50`.

## Smoke Test

Create a few dummy MP3 files and run:

```bash
bun src/cli.js --input ./fixtures/input --output ./fixtures/output --folders 3 --clean --seed demo
```
