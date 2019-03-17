workflow "pylint on push" {
  on = "push"
  resolves = ["GitHub Action for pylint"]
}

action "GitHub Action for pylint" {
  uses = "cclauss/GitHub-Action-for-pylint@0.6.1"
}

workflow "LGTM" {
  on = "push"
  resolves = ["HTTP client"]
}

action "HTTP client" {
  uses = "swinton/httpie.action@8ab0a0e926d091e0444fcacd5eb679d2e2d4ab3d"
  args = ["POST", "https://lgtm.com/api/v1.0/analyses/1507985346060?commit=latest", "Authorization: Bearer $LGTM_TOKEN"]
  secrets = ["LGTM_TOKEN"]
}

action "GitHub Action for Docker on ARM" {
  uses = "lennart-k/docker-arm-build@master"
  runs = "docker build ."
}
