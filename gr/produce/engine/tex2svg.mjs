// Renders TeX to standalone SVG files with MathJax (no browser, no network).
//   node tex2svg.mjs <jobs.json>   jobs = [{ "tex": "...", "out": "path.svg", "color": "#111827" }]
import { readFileSync, writeFileSync } from "node:fs";
import { mathjax } from "mathjax-full/js/mathjax.js";
import { TeX } from "mathjax-full/js/input/tex.js";
import { SVG } from "mathjax-full/js/output/svg.js";
import { liteAdaptor } from "mathjax-full/js/adaptors/liteAdaptor.js";
import { RegisterHTMLHandler } from "mathjax-full/js/handlers/html.js";
import { AllPackages } from "mathjax-full/js/input/tex/AllPackages.js";

const adaptor = liteAdaptor();
RegisterHTMLHandler(adaptor);
const doc = mathjax.document("", {
  InputJax: new TeX({ packages: AllPackages }),
  OutputJax: new SVG({ fontCache: "none" }),
});

const jobs = JSON.parse(readFileSync(process.argv[2], "utf8"));
for (const job of jobs) {
  const node = doc.convert(job.tex, { display: true, em: 16, ex: 8, containerWidth: 1000 });
  let svg = adaptor.innerHTML(node);
  if (svg.includes('data-mjx-error')) throw new Error(`TeX error in: ${job.tex}`);
  // MathJax sizes in ex; drop its size and inline style, keep the viewBox and let CSS size it.
  // The aspect (viewBox w/h) is written next to the file so layouts can size equations evenly.
  svg = svg
    .replace(/ style="[^"]*"/, "")
    .replace(/ width="[^"]*"/, "")
    .replace(/ height="[^"]*"/, "")
    .replace("<svg ", `<svg style="color:${job.color || "#111827"}" `);
  // MathJax's box is tight and some glyphs (k, h, W) overhang it: pad 4% each side, 8% top/bottom.
  const vb = svg.match(/viewBox="([-\d.]+) ([-\d.]+) ([-\d.]+) ([-\d.]+)"/);
  if (vb) {
    let [x, y, w, h] = vb.slice(1).map(Number);
    const px = w * 0.04, py = h * 0.08;
    [x, y, w, h] = [x - px, y - py, w + 2 * px, h + 2 * py];
    svg = svg.replace(vb[0], `viewBox="${x} ${y} ${w} ${h}"`);
    job.aspect = +(w / h).toFixed(3);
  } else job.aspect = 4;
  writeFileSync(job.out, svg);
}
writeFileSync(process.argv[2], JSON.stringify(jobs, null, 1));
console.log(`tex2svg: ${jobs.length} equations`);
