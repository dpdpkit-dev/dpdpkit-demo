// Copies the published @dpdpkit/embed bundle next to the other built files, so the plain-HTML page can load it
// with a script tag. (On a real site the tag points at jsDelivr.) Runs after `vite build`, which empties the folder.
import { copyFileSync, mkdirSync } from "node:fs";

mkdirSync("app/static/dist", { recursive: true });
copyFileSync("node_modules/@dpdpkit/embed/dist/embed.js", "app/static/dist/embed.js");
