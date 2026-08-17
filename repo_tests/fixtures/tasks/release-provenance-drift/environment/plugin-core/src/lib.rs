//! Primary shared library entry; generated ABI lives under `OUT_DIR`.

use std::os::raw::c_char;

#[cfg(debug_assertions)]
const PROFILE_NOTE: &[u8] = b"debug-profile\0";
#[cfg(not(debug_assertions))]
const PROFILE_NOTE: &[u8] = b"release-profile\0";

const BUILD_NOTE: &[u8] = b"surface-anchor-v1\0";

#[no_mangle]
pub extern "C" fn plugin_profile_tag() -> *const c_char {
    PROFILE_NOTE.as_ptr().cast()
}

#[no_mangle]
pub extern "C" fn plugin_profile_tag_len() -> usize {
    PROFILE_NOTE.len().saturating_sub(1)
}

#[no_mangle]
pub extern "C" fn plugin_build_note() -> *const c_char {
    BUILD_NOTE.as_ptr().cast()
}

#[no_mangle]
pub extern "C" fn plugin_build_note_len() -> usize {
    BUILD_NOTE.len().saturating_sub(1)
}

include!(concat!(env!("OUT_DIR"), "/generated/ffi.rs"));
