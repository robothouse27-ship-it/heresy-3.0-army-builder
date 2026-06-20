#!/usr/bin/env node
/* Encrypt the rules bundle so a PUBLIC repo only ever contains ciphertext.
   Reads app/data.js (plaintext bundle, git-ignored) -> writes app/data.enc.js.
   Crypto: PBKDF2(SHA-256, 200k) -> AES-256-GCM. Decrypted in-browser via Web Crypto.
   Layout of the blob (base64): salt(16) | iv(12) | ciphertext | authTag(16).

   Usage:  PW='YourPassphrase' node build/encrypt.js
           (PW is required — there is no default passphrase) */
const crypto = require("crypto");
const fs = require("fs");
const path = require("path");

const ROOT = path.dirname(__dirname);
const PW = process.env.PW;
if (!PW) { console.error("Set the passphrase: PW='…' node build/encrypt.js"); process.exit(1); }
const ITER = 200000;

global.window = {};
require(path.join(ROOT, "app", "data.js"));        // sets window.GAME_DATA
const plaintext = JSON.stringify(global.window.GAME_DATA);

const salt = crypto.randomBytes(16);
const iv = crypto.randomBytes(12);
const key = crypto.pbkdf2Sync(PW, salt, ITER, 32, "sha256");
const cipher = crypto.createCipheriv("aes-256-gcm", key, iv);
const ct = Buffer.concat([cipher.update(plaintext, "utf8"), cipher.final()]);
const tag = cipher.getAuthTag();
const blob = Buffer.concat([salt, iv, ct, tag]).toString("base64");

const out = path.join(ROOT, "app", "data.enc.js");
fs.writeFileSync(out,
  "// AUTO-GENERATED encrypted rules bundle. Safe to publish. Decrypts in-browser with the passphrase.\n" +
  "window.ENC_BUNDLE=\"" + blob + "\";\nwindow.ENC_ITER=" + ITER + ";\n");

console.log(`Wrote ${out}`);
console.log(`  passphrase: (from $PW)`);
console.log(`  plaintext: ${plaintext.length} chars -> ciphertext blob: ${blob.length} base64 chars`);
