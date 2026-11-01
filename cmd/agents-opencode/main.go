package main

import (
	"fmt"
	"github.com/beltet/agents-opencode/internal/manager"
	"os"
)

func main() {
	if err := manager.Launch(os.Args[1:], os.Stdin, os.Stdout); err != nil {
		fmt.Fprintln(os.Stderr, "Error:", err)
		os.Exit(1)
	}
}
