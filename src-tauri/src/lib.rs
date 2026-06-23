use serde::{Deserialize, Serialize};
use std::fs;
use std::path::{Path, PathBuf};
use thiserror::Error;

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct MixOptions {
    input_folder: String,
    output_folder: String,
    folder_count: usize,
    files_per_folder: Option<usize>,
    prefix_files: bool,
    clean_output: bool,
    seed: Option<String>,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
struct MixResult {
    input_folder: String,
    output_folder: String,
    source_file_count: usize,
    files_per_folder: usize,
    generated_folders: Vec<String>,
}

#[derive(Debug, Error)]
enum MixError {
    #[error("Input folder is required")]
    MissingInput,
    #[error("Output folder is required")]
    MissingOutput,
    #[error("Number of folders must be greater than 0")]
    InvalidFolderCount,
    #[error("Number of files per folder must be greater than 0")]
    InvalidFilesPerFolder,
    #[error("Number of files per folder cannot be greater than available MP3 files ({0})")]
    TooManyFilesPerFolder(usize),
    #[error("No .mp3 files found in {0}")]
    NoMp3Files(String),
    #[error("Could not read folder {path}: {source}")]
    ReadFolder { path: String, source: std::io::Error },
    #[error("Could not create folder {path}: {source}")]
    CreateFolder { path: String, source: std::io::Error },
    #[error("Could not clean output folder {path}: {source}")]
    CleanFolder { path: String, source: std::io::Error },
    #[error("Could not copy {from} to {to}: {source}")]
    CopyFile { from: String, to: String, source: std::io::Error },
    #[error("Could not open {path}: {source}")]
    OpenPath { path: String, source: std::io::Error },
}

impl serde::Serialize for MixError {
    fn serialize<S>(&self, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: serde::Serializer,
    {
        serializer.serialize_str(&self.to_string())
    }
}

#[tauri::command]
fn select_folder() -> Option<String> {
    rfd::FileDialog::new()
        .pick_folder()
        .map(|path| path.to_string_lossy().to_string())
}

#[tauri::command]
fn open_path(path: String) -> Result<(), MixError> {
    open::that(&path).map_err(|source| MixError::OpenPath { path, source })
}

#[tauri::command]
fn mix_files(options: MixOptions) -> Result<MixResult, MixError> {
    validate_options(&options)?;

    let input_folder = PathBuf::from(options.input_folder.trim());
    let output_folder = PathBuf::from(options.output_folder.trim());
    let files = get_mp3_files(&input_folder)?;
    let files_per_folder = options.files_per_folder.unwrap_or(files.len());
    let mut random = SeededRandom::new(options.seed.as_deref());
    let mut generated_folders = Vec::with_capacity(options.folder_count);

    if files_per_folder > files.len() {
        return Err(MixError::TooManyFilesPerFolder(files.len()));
    }

    if options.clean_output && output_folder.exists() {
        fs::remove_dir_all(&output_folder).map_err(|source| MixError::CleanFolder {
            path: output_folder.to_string_lossy().to_string(),
            source,
        })?;
    }

    create_folder(&output_folder)?;

    for folder_index in 0..options.folder_count {
        let folder_name = format_number(folder_index + 1, options.folder_count);
        let target_folder = output_folder.join(folder_name);
        let shuffled_files = shuffle_files(&files, &mut random)
            .into_iter()
            .take(files_per_folder)
            .collect::<Vec<_>>();

        create_folder(&target_folder)?;

        for (file_index, file_name) in shuffled_files.iter().enumerate() {
            let target_name = if options.prefix_files {
                format!(
                    "{}_{}",
                    format_number(file_index + 1, shuffled_files.len()),
                    file_name
                )
            } else {
                file_name.clone()
            };

            let from = input_folder.join(file_name);
            let to = target_folder.join(target_name);
            fs::copy(&from, &to).map_err(|source| MixError::CopyFile {
                from: from.to_string_lossy().to_string(),
                to: to.to_string_lossy().to_string(),
                source,
            })?;
        }

        generated_folders.push(target_folder.to_string_lossy().to_string());
    }

    Ok(MixResult {
        input_folder: input_folder.to_string_lossy().to_string(),
        output_folder: output_folder.to_string_lossy().to_string(),
        source_file_count: files.len(),
        files_per_folder,
        generated_folders,
    })
}

fn validate_options(options: &MixOptions) -> Result<(), MixError> {
    if options.input_folder.trim().is_empty() {
        return Err(MixError::MissingInput);
    }

    if options.output_folder.trim().is_empty() {
        return Err(MixError::MissingOutput);
    }

    if options.folder_count == 0 {
        return Err(MixError::InvalidFolderCount);
    }

    if matches!(options.files_per_folder, Some(0)) {
        return Err(MixError::InvalidFilesPerFolder);
    }

    Ok(())
}

fn get_mp3_files(input_folder: &Path) -> Result<Vec<String>, MixError> {
    let entries = fs::read_dir(input_folder).map_err(|source| MixError::ReadFolder {
        path: input_folder.to_string_lossy().to_string(),
        source,
    })?;

    let mut files = entries
        .filter_map(Result::ok)
        .filter(|entry| entry.path().is_file())
        .filter_map(|entry| {
            let path = entry.path();
            let is_mp3 = path
                .extension()
                .and_then(|extension| extension.to_str())
                .is_some_and(|extension| extension.eq_ignore_ascii_case("mp3"));

            is_mp3.then(|| entry.file_name().to_string_lossy().to_string())
        })
        .collect::<Vec<_>>();

    files.sort_by_key(|file| file.to_lowercase());

    if files.is_empty() {
        return Err(MixError::NoMp3Files(input_folder.to_string_lossy().to_string()));
    }

    Ok(files)
}

fn create_folder(path: &Path) -> Result<(), MixError> {
    fs::create_dir_all(path).map_err(|source| MixError::CreateFolder {
        path: path.to_string_lossy().to_string(),
        source,
    })
}

fn format_number(value: usize, max: usize) -> String {
    let width = max.to_string().len();
    format!("{value:0width$}")
}

fn shuffle_files(files: &[String], random: &mut SeededRandom) -> Vec<String> {
    let mut shuffled = files.to_vec();

    for index in (1..shuffled.len()).rev() {
        let target_index = random.next_index(index + 1);
        shuffled.swap(index, target_index);
    }

    shuffled
}

struct SeededRandom {
    state: u32,
    random_seed: bool,
}

impl SeededRandom {
    fn new(seed: Option<&str>) -> Self {
        match seed.filter(|value| !value.trim().is_empty()) {
            Some(seed_text) => {
                let mut state = 2_166_136_261u32;
                for byte in seed_text.bytes() {
                    state ^= byte as u32;
                    state = state.wrapping_mul(16_777_619);
                }

                Self {
                    state,
                    random_seed: false,
                }
            }
            None => Self {
                state: 0,
                random_seed: true,
            },
        }
    }

    fn next_index(&mut self, upper_bound: usize) -> usize {
        if self.random_seed {
            use std::time::{SystemTime, UNIX_EPOCH};

            let nanos = SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .map(|duration| duration.subsec_nanos())
                .unwrap_or(0);
            self.state ^= nanos;
        }

        self.state = self.state.wrapping_add(0x6D2B79F5);
        let mut value = self.state;
        value = (value ^ (value >> 15)).wrapping_mul(value | 1);
        value ^= value.wrapping_add((value ^ (value >> 7)).wrapping_mul(value | 61));
        (((value ^ (value >> 14)) as u64 * upper_bound as u64) >> 32) as usize
    }
}

pub fn run() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![select_folder, open_path, mix_files])
        .run(tauri::generate_context!())
        .expect("failed to run Mix Files app");
}
