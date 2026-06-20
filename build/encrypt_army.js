#!/usr/bin/env node
/* Encrypt one army bundle JSON -> app/data.<id>.enc.js (ciphertext only).
   Same crypto as encrypt.js (PBKDF2-SHA256 200k -> AES-256-GCM), same blob
   layout. Each file assigns window.ENC_ARMY (read immediately after load).
   Usage: PW='YourPassphrase' node build/encrypt_army.js <bundle.json> <out.enc.js>
   (PW is required — there is no default passphrase) */
const crypto = require("crypto"), fs = require("fs");
const [,, inPath, outPath] = process.argv;
const PW = process.env.PW, ITER = 200000;
if (!PW) { console.error("Set the passphrase: PW='…' node build/encrypt_army.js <in> <out>"); process.exit(1); }
const plaintext = fs.readFileSync(inPath, "utf8");
const salt = crypto.randomBytes(16), iv = crypto.randomBytes(12);
const key = crypto.pbkdf2Sync(PW, salt, ITER, 32, "sha256");
const cipher = crypto.createCipheriv("aes-256-gcm", key, iv);
const ct = Buffer.concat([cipher.update(plaintext, "utf8"), cipher.final()]);
const blob = Buffer.concat([salt, iv, ct, cipher.getAuthTag()]).toString("base64");
fs.writeFileSync(outPath,
  "// AUTO-GENERATED encrypted army bundle. Safe to publish.\n" +
  "window.ENC_ARMY=\"" + blob + "\";\nwindow.ENC_ARMY_ITER=" + ITER + ";\n");
console.log(`Wrote ${outPath} (${blob.length} b64 chars)`);
