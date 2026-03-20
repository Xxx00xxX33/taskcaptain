use std::cmp::Reverse;
use std::env;
use std::fs::{self, File};
use std::io::{self, Read, Seek, SeekFrom, Write};
use std::path::{Path, PathBuf};
use std::time::UNIX_EPOCH;

#[derive(Debug, Clone)]
struct Artifact {
    rel_path: String,
    name: String,
    size: u64,
    mtime: u64,
}

fn main() {
    if let Err(err) = run() {
        let _ = writeln!(io::stderr(), "{err}");
        std::process::exit(1);
    }
}

fn run() -> Result<(), String> {
    let args: Vec<String> = env::args().collect();
    if args.len() < 2 {
        return Err("usage: taskcaptain-fastview <tail|artifacts> ...".into());
    }
    match args[1].as_str() {
        "tail" => {
            if args.len() != 4 {
                return Err("usage: taskcaptain-fastview tail <path> <bytes>".into());
            }
            let path = PathBuf::from(&args[2]);
            let max_bytes = args[3]
                .parse::<u64>()
                .map_err(|_| "invalid byte count".to_string())?;
            let data = read_tail(&path, max_bytes).map_err(|e| e.to_string())?;
            let mut out = io::stdout();
            out.write_all(&data).map_err(|e| e.to_string())?;
            Ok(())
        }
        "artifacts" => {
            if args.len() != 4 {
                return Err("usage: taskcaptain-fastview artifacts <workspace> <limit>".into());
            }
            let workspace = PathBuf::from(&args[2]);
            let limit = args[3]
                .parse::<usize>()
                .map_err(|_| "invalid limit".to_string())?;
            let (items, total) = collect_artifacts(&workspace, limit).map_err(|e| e.to_string())?;
            let mut out = io::stdout();
            for item in items {
                writeln!(
                    out,
                    "{}\t{}\t{}\t{}",
                    item.mtime, item.size, item.rel_path, item.name
                )
                .map_err(|e| e.to_string())?;
            }
            writeln!(out, "TOTAL\t{total}").map_err(|e| e.to_string())?;
            Ok(())
        }
        _ => Err("unknown command".into()),
    }
}

fn read_tail(path: &Path, max_bytes: u64) -> io::Result<Vec<u8>> {
    let mut file = File::open(path)?;
    let size = file.metadata()?.len();
    let start = size.saturating_sub(max_bytes);
    file.seek(SeekFrom::Start(start))?;
    let mut buf = Vec::new();
    file.read_to_end(&mut buf)?;
    Ok(buf)
}

fn collect_artifacts(workspace: &Path, limit: usize) -> io::Result<(Vec<Artifact>, usize)> {
    if !workspace.exists() {
        return Ok((Vec::new(), 0));
    }

    let mut stack = vec![workspace.to_path_buf()];
    let mut artifacts: Vec<Artifact> = Vec::new();
    let mut total = 0usize;

    while let Some(dir) = stack.pop() {
        for entry in fs::read_dir(&dir)? {
            let entry = entry?;
            let path = entry.path();
            let file_type = entry.file_type()?;
            if file_type.is_dir() {
                if should_skip_dir(&path) {
                    continue;
                }
                stack.push(path);
                continue;
            }
            if !file_type.is_file() {
                continue;
            }
            let metadata = entry.metadata()?;
            total += 1;
            let rel = path
                .strip_prefix(workspace)
                .unwrap_or(&path)
                .to_string_lossy()
                .replace('\\', "/");
            let name = path
                .file_name()
                .and_then(|v| v.to_str())
                .unwrap_or_default()
                .to_string();
            let mtime = metadata
                .modified()
                .ok()
                .and_then(|ts| ts.duration_since(UNIX_EPOCH).ok())
                .map(|d| d.as_secs())
                .unwrap_or(0);
            artifacts.push(Artifact {
                rel_path: rel,
                name,
                size: metadata.len(),
                mtime,
            });
        }
    }

    artifacts.sort_by_key(|item| {
        (
            pinned_rank(&item.name),
            Reverse(item.mtime),
            item.rel_path.clone(),
        )
    });
    artifacts.truncate(limit);
    Ok((artifacts, total))
}

fn should_skip_dir(path: &Path) -> bool {
    let name = path.file_name().and_then(|v| v.to_str()).unwrap_or_default();
    matches!(
        name,
        ".git" | ".taskcaptain" | ".venv" | "venv" | "node_modules" | "__pycache__"
    )
}

fn pinned_rank(name: &str) -> usize {
    match name {
        "README.md" => 0,
        "verification.log" => 1,
        "index.html" => 2,
        "app.js" => 3,
        "styles.css" => 4,
        _ => 999,
    }
}
