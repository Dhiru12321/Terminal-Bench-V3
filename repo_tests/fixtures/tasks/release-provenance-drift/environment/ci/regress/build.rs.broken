use sha2::{Digest, Sha256};
use std::env;
use std::fs;
use std::path::Path;

fn main() {
    let manifest_dir = env::var("CARGO_MANIFEST_DIR").expect("CARGO_MANIFEST_DIR");
    let out_dir = env::var("OUT_DIR").expect("OUT_DIR");
    let tpl_path = Path::new(&manifest_dir).join("../codegen/templates/ffi.rs.tpl");
    println!("cargo:rerun-if-changed={}", tpl_path.display());

    let tpl = fs::read_to_string(&tpl_path).expect("read template");
    let mut hasher = Sha256::new();
    hasher.update(tpl.as_bytes());
    let full = format!("{:x}", hasher.finalize());
    let epoch: String = full.chars().take(24).collect();

    let generated = tpl.replace("@@EPOCH@@", &epoch);
    let gen_dir = Path::new(&out_dir).join("generated");
    fs::create_dir_all(&gen_dir).expect("mkdir generated");
    fs::write(gen_dir.join("ffi.rs"), generated).expect("write ffi.rs");

    fs::write(
        Path::new(&out_dir).join("prov_epoch.txt"),
        format!("{epoch}\n"),
    )
    .expect("write epoch");
}
