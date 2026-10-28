const {test}=require('node:test');
const assert=require('node:assert/strict');
const path=require('node:path');
const {lessonKey,inside,apiPath}=require('../src/core.cjs');
test('only curriculum lesson IDs become file paths',()=>{
 assert.equal(lessonKey('V01',['V01']),'V01');
 for(const key of ['../V01','V99','T01.py','/tmp/x',null])assert.throws(()=>lessonKey(key,['V01']));
});
test('directory boundary does not accept siblings',()=>{
 const root=path.resolve('space');assert.ok(inside(root,path.join(root,'exercises','P01.py')));
 assert.ok(!inside(root,path.resolve('space-other','P01.py')));assert.ok(!inside(root,path.join(root,'..','private')));
});
test('bridge accepts application operations only',()=>{
 for(const route of ['/bootstrap','/lesson/T03/examples','/lesson/V01/reference','/jobs/abcdef/stop','/settings/course.S12','/workspace/reset/P01','/clear'])assert.equal(apiPath(route),route);
 for(const route of ['http://other/','/shutdown','/assets/../../x','/lesson/../x','/lesson/T03/examples/../../private','//bootstrap','/settings/private'])assert.throws(()=>apiPath(route));
});

test('saved view state is restricted to existing lessons and courses',()=>{
 const {navigationState}=require('../src/core.cjs');
 assert.deepEqual(navigationState({page:'practice',lesson:'V01',course:'S12'},['P01','V01'],['S12']),{page:'practice',lesson:'V01',course:'S12'});
 assert.deepEqual(navigationState({page:'unknown',lesson:'../file',course:'X'},['P01'],['S00']),{page:'home',lesson:'P01',course:null});
});

test('engineering view migration and separate last-learning memory',()=>{
 const {navigationState}=require('../src/core.cjs');
 const value=navigationState({page:'practice',lesson:'E05',lastBasic:'V13',lastProject:'E05',lastLearning:'E05',trail:[{page:'practice',lesson:'V13'}],memory:{'E05.file':'checkpoint.py'}},['P01','V13','E05'],['S28']);
 assert.equal(value.page,'project');assert.equal(value.lastBasic,'V13');assert.equal(value.trail[0].page,'practice');assert.equal(value.memory['E05.file'],'checkpoint.py');
});
