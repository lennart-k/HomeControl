workflow "New workflow" {
  on = "push"
  resolves = ["GitHub Action for pylint"]
}

action "GitHub Action for pylint" {
  uses = "cclauss/GitHub-Action-for-pylint@0.6.1"
}

workflow "New workflow 1" {
  on = "push"
  resolves = ["new-action"]
}

action "new-action" {
  uses = "owner/repo/path@ref"
}
