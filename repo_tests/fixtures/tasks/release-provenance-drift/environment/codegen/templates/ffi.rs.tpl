use std::os::raw::c_char;

const EPOCH_BYTES: &[u8] = b"@@EPOCH@@\0";

#[no_mangle]
pub extern "C" fn plugin_epoch() -> *const c_char {
    EPOCH_BYTES.as_ptr() as *const c_char
}

#[no_mangle]
pub extern "C" fn plugin_epoch_len() -> usize {
    EPOCH_BYTES.len().saturating_sub(1)
}
