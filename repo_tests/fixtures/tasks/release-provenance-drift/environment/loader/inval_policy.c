#include <sys/stat.h>

int cache_still_valid(const char *plugin_path, const char *seal_path) {
  struct stat a;
  (void)seal_path;
  if (!plugin_path) {
    return 0;
  }
  if (stat(plugin_path, &a) != 0) {
    return 0;
  }
  return 1;
}
