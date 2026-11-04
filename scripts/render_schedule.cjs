// Inspect generated slide markup offline. This is not a browser/layout check.
const vm = require('node:vm');
const fs = require('node:fs');
const script = fs.readFileSync(0, 'utf8');
const elements = {};
function element() {
  return {style: {}, classList: {add(){}, remove(){}, toggle(){}},
    addEventListener(){}, querySelectorAll(){return []}, setAttribute(){},
    textContent: '', innerHTML: ''};
}
const document = {getElementById(id){return elements[id] ??= element()},
  querySelector(){return element()}, addEventListener(){}, body: element()};
const context = {document, window: {innerWidth:1280, innerHeight:720,
  addEventListener(){}, setTimeout(){}, clearTimeout(){}},
  localStorage: {getItem(){return null}, setItem(){}},
  innerWidth:1280, innerHeight:720, setTimeout(){}, clearTimeout(){}};
vm.createContext(context);
try {
  vm.runInContext(script, context, {timeout: 2000});
  const result = vm.runInContext(`({show_schedule: meeting.show_schedule,
    rows: slides.map((s,i)=>({s,i})).filter(({s})=>
      ['role','speech','break'].includes(s.type) || s.time).map(({s,i})=>({
        title:s.title, time:s.time,
        html: typeof render === 'function' ? render(s) : renderSlide(s,i)
      }))})`, context, {timeout:2000});
  process.stdout.write(JSON.stringify(result));
} catch (error) {
  process.stderr.write(String(error)); process.exitCode = 1;
}
