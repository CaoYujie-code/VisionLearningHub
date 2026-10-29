'use strict';
const path = require('node:path');
function lessonKey(value, known) {
  if (typeof value !== 'string' || !/^[A-Z]\d{2}$/.test(value) || !known.includes(value)) throw new Error('未知练习');
  return value;
}
function inside(root, file) {
  const rel = path.relative(path.resolve(root), path.resolve(file));
  return rel === '' || (!rel.startsWith('..' + path.sep) && rel !== '..' && !path.isAbsolute(rel));
}
function apiPath(value) {
  if (typeof value !== 'string' || !/^\/(bootstrap|function-review|projects\/[A-Z]\d{2}(\/(export|guide))?|lesson\/[A-Z]\d{2}(\/(reference|examples|walkthrough(\/(demo|progress|import|files\/\d{1,4}|export\/\d{1,4}))?))?|jobs(\/[a-f0-9]+(\/stop)?)?|settings\/(bookmarks|course\.[A-Z]\d{2})|lab|upload|records(\/\d+)?|environment|backup|restore|export-code|clear|workspace\/reset\/[A-Z]\d{2})$/.test(value)) throw new Error('不支持的接口');
  return value;
}
function navigationState(value, lessons, courses) {
  const page=['home','route','projects','project','lab','practice','resources','records'].includes(value?.page)?value.page:'home';
  const result={page:page==='practice'&&value?.lesson?.startsWith('E')?'project':page,lesson:lessons.includes(value?.lesson)?value.lesson:(lessons[0]||'P01'),course:courses.includes(value?.course)?value.course:null};
  for(const field of ['lastBasic','lastProject','lastLearning'])if(lessons.includes(value?.[field]))result[field]=value[field];
  if(Array.isArray(value?.trail))result.trail=value.trail.slice(-30).map(v=>navigationState({page:v.page,lesson:v.lesson,course:v.course},lessons,courses));
  if(value?.memory&&typeof value.memory==='object'&&JSON.stringify(value.memory).length<30000)result.memory=value.memory;
  return result;
}
module.exports = { lessonKey, inside, apiPath, navigationState };
