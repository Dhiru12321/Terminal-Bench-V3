#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "inval_policy.c"


static char *slurp(const char *path) {
  FILE *f = fopen(path, "rb");
  long sz;
  char *buf;
  if (!f) {
    return NULL;
  }
  fseek(f, 0, SEEK_END);
  sz = ftell(f);
  fseek(f, 0, SEEK_SET);
  buf = malloc((size_t)sz + 1);
  if (!buf) {
    fclose(f);
    return NULL;
  }
  fread(buf, 1, (size_t)sz, f);
  buf[sz] = 0;
  fclose(f);
  return buf;
}

static int extract_epoch_json(const char *json, char *out, size_t outsz) {
  const char *k = strstr(json, "\"epoch\"");
  if (!k) {
    return -1;
  }
  k = strchr(k, ':');
  if (!k) {
    return -1;
  }
  k = strchr(k, '"');
  if (!k) {
    return -1;
  }
  k++;
  {
    size_t i = 0;
    while (k[i] && k[i] != '"' && i + 1 < outsz) {
      out[i] = k[i];
      i++;
    }
    out[i] = 0;
  }
  return 0;
}

int main(int argc, char **argv) {
  const char *so = argc > 1 ? argv[1] : "/app/out/pkg/bin/libplugin_core.so";
  const char *seal = argc > 2 ? argv[2] : "/app/out/pkg/seal.json";
  char *js;
  char want[128];
  void *h;
  const char *(*ep)(void);
  size_t (*eln)(void);

  js = slurp(seal);
  if (!js) {
    fprintf(stderr, "cannot read seal\n");
    return 2;
  }
  if (extract_epoch_json(js, want, sizeof want) != 0) {
    free(js);
    fprintf(stderr, "bad seal\n");
    return 3;
  }
  free(js);

  if (!cache_still_valid(so, seal)) {
    fprintf(stderr, "cache invalid\n");
    return 4;
  }

  h = dlopen(so, RTLD_NOW);
  if (!h) {
    fprintf(stderr, "dlopen: %s\n", dlerror());
    return 5;
  }
  ep = (const char *(*)(void))dlsym(h, "plugin_epoch");
  eln = (size_t (*)(void))dlsym(h, "plugin_epoch_len");
  if (!ep || !eln) {
    fprintf(stderr, "missing exports\n");
    return 6;
  }
  {
    const char *got = ep();
    size_t n = eln();
    size_t wn = strlen(want);
    if (n != wn || strncmp(got, want, n) != 0) {
      fprintf(stderr, "epoch mismatch\n");
      return 7;
    }
  }
  dlclose(h);
  return 0;
}
