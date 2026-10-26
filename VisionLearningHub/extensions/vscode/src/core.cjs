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
  if (typeof value !== 'string' || !/^\/(bootstrap|lesson\/[A-Z]\d{2}(\/reference)?|jobs(\/[a-f0-9]+(\/stop)?)?|settings\/(bookmarks|course\.[A-Z]\d{2})|lab|upload|records(\/\d+)?|environment|backup|restore|export-code|clear|workspace\/reset\/[A-Z]\d{2})$/.test(value)) throw new Error('不支持的接口');
  return value;
}
module.exports = { lessonKey, inside, apiPath };
