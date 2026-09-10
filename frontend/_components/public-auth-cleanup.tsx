"use client";

import { useEffect } from "react";

/* Chave comuns que podem guardar token no localStorage */
const POSSIBLE_TOKEN_KEYS = ["access_token", "token", "auth_token"];

export function PublicAuthCleanup() {
  useEffect(() => {
    // 1. limpar tokens do LocalStorage (lado cliente)
    for (const key of POSSIBLE_TOKEN_KEYS) {
      localStorage.removeItem(key);
    }

    // 2. Garante limpeza do cookie via endpoint de logout
    // idempotente: pode chamar várias vezes sem problemas
    fetch("/api/auth/logout", {
      method: "POST",
      credentials: "include",
    }).catch(() => {
      /* Ignora erros, não é crítico */
    });
  }, []);

  return null;
}
