package pr.gates

default allow = false

allow {
  input.coverage >= 0.8
}

deny[msg] {
  input.secrets_found > 0
  msg := "secrets detected"
}
