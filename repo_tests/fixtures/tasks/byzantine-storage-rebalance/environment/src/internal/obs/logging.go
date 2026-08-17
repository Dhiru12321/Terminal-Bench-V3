package obs

import (
	"log"
	"os"
)

// Logger is a tiny wrapper so packages can opt into stderr diagnostics without importing many symbols.
var Logger = log.New(os.Stderr, "storesim ", log.LstdFlags|log.Lmicroseconds)
