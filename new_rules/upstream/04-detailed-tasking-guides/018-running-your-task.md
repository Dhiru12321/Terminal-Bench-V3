---
title: "Running Your Task"
section: "Detailed Tasking Guides"
source: "https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/creating-tasks/videos/running-your-task"
captured: 2026-08-12
---

# Video: Running Your Task

Learn how to interact with your task environment and test your solution locally.

## Video Tutorial

#### Running Your Task

[Running Your Task](https://www.loom.com/embed/22449b76123d41e6abff0efb39d0b960?hide_owner=true&hide_share=true&hide_title=true&hideEmbedTopBar=true)

## What You'll Learn

- How to start your task container in interactive mode
- Navigating the task environment
- Testing commands before adding them to your solution
- Debugging environment issues

## Key Commands

### Start Interactive Mode

```bash
stb harbor tasks start-env -p <task-folder> -i
```

### Inside the Container

Once inside, you can:

- Navigate the filesystem
- Run your solution commands
- Test that everything works as expected
- Debug any issues

### Exit the Container

```bash
exit
```

## Tips

1. **Test everything manually first** — Run each command of your solution inside the container before writing `solve.sh`
2. **Check file paths** — Verify that all paths in `instruction.md` exist
3. **Verify dependencies** — Make sure all required packages are installed
4. **Note exact commands** — Copy the working commands for your solution file

## Common Issues

| Problem | Solution |
| --- | --- |
| Container won't start | Check Docker is running |
| Permission denied | Run Docker Desktop with admin rights |
| Missing packages | Add to environment/Dockerfile and rebuild |
| Wrong working directory | Check WORKDIR in environment/Dockerfile |

---

## Related Videos

- [Writing oracle solution](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/creating-tasks/writing-oracle-solution)
- [Writing tests](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/creating-tasks/writing-tests)

---

[Previous: Creating a Task](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/creating-tasks/videos/creating-task) · [Next: Docker Environment Setup](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/creating-tasks/creating-docker-environment)
