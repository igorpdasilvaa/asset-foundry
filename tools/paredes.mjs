// Calcula as paredes do Foundry com o mesmo código do módulo (scripts/mapa.js), para a prévia.
// Entrada (stdin): { cols, rows, solid: ["x,y"], doors: [{x,y,dir}], pillars: [{x,y}] }. Saída: JSON das paredes.
globalThis.Hooks = { on() {} };
const { computeWalls } = await import("../scripts/mapa.js");
let input = "";
for await (const chunk of process.stdin) input += chunk;
const st = JSON.parse(input);
process.stdout.write(JSON.stringify(computeWalls({ ...st, solid: new Set(st.solid) })));
