'use strict';
const vscode=require('vscode');
const fs=require('node:fs/promises');
const path=require('node:path');
const crypto=require('node:crypto');
const {latest,download}=require('./updates.cjs');
class Updater{
  constructor(context,output){this.context=context;this.output=output;this.controllers=new Set();this.fetcher=fetch;this.notify=(...args)=>vscode.window.showInformationMessage(...args);}
  schedule(){
    if(!vscode.workspace.getConfiguration('visionLearning').get('checkUpdates',true))return;
    const previous=this.context.globalState.get('lastUpdateCheck',0);
    if(Date.now()-previous<24*60*60*1000)return;
    this.timer=setTimeout(()=>this.check(false),10000);
  }
  async token(interactive=false){
    const session=await vscode.authentication.getSession('github',['repo'],interactive?{createIfNone:true}:{silent:true});
    return session?.accessToken;
  }
  async check(interactive=false,login=false){
    if(this.busy)return false;this.busy=true;
    const controller=new AbortController();this.controllers.add(controller);const timeout=setTimeout(()=>controller.abort(),20000);
    try{
      const token=await this.token(login);const current=this.context.extension.packageJSON.version;
      const update=await latest(current,{token,signal:controller.signal,fetcher:this.fetcher});
      await this.context.globalState.update('lastUpdateCheck',Date.now());
      if(!update){if(interactive)await vscode.window.showInformationMessage('当前 '+current+' 已是最新发布版本。');return false;}
      if(!interactive&&this.context.globalState.get('ignoredUpdate')===update.version)return false;
      const choice=await vscode.window.showInformationMessage('视觉学习 '+update.version+' 已发布。当前版本 '+current+'，更新后按提示重载窗口。','更新','查看发布说明','稍后');
      if(choice==='查看发布说明')await vscode.env.openExternal(vscode.Uri.parse(update.page));
      else if(choice==='更新')return await this.install(update,token);
      else if(choice==='稍后')await this.context.globalState.update('ignoredUpdate',update.version);
      return false;
    }catch(error){
      this.output.appendLine('更新检查：'+error.message);
      if(interactive){
        if(error.code==='NOT_FOUND'&&!login){const choice=await vscode.window.showWarningMessage('未找到可读取的发布版本。仓库若为私有，可授权 VS Code 登录 GitHub 后重试。','登录 GitHub 并重试','查看发布页');
          if(choice==='登录 GitHub 并重试'){this.busy=false;return this.check(true,true);}
          if(choice==='查看发布页')await vscode.env.openExternal(vscode.Uri.parse('https://github.com/CaoYujie-code/VisionLearningHub/releases'));
        }else await vscode.window.showWarningMessage('更新未完成：'+error.message);
      }return false;
    }finally{clearTimeout(timeout);this.controllers.delete(controller);this.busy=false;}
  }
  async install(update,token){
    const directory=vscode.Uri.file(path.join(this.context.globalStorageUri.fsPath,'updates'));await vscode.workspace.fs.createDirectory(directory);
    const file=vscode.Uri.joinPath(directory,crypto.randomBytes(8).toString('hex')+'-'+update.name);
    let installed=false;
    try{
      await vscode.window.withProgress({location:vscode.ProgressLocation.Notification,title:'更新视觉学习到 '+update.version,cancellable:true},async(progress,cancel)=>{
        const controller=new AbortController();this.controllers.add(controller);const timeout=setTimeout(()=>controller.abort(),120000);
        const listener=cancel.onCancellationRequested(()=>controller.abort());
        try{
          progress.report({message:'下载并校验安装包…'});
          const bytes=await download(update,this.context.extension.id,{token,signal:controller.signal,fetcher:this.fetcher});
          if(cancel.isCancellationRequested)throw new Error('已取消更新');
          await vscode.workspace.fs.writeFile(file,bytes);
          progress.report({message:'安装新版扩展…'});
          await vscode.commands.executeCommand('workbench.extensions.installExtension',file,{installOnlyNewlyAddedFromExtensionPackVSIX:false});installed=true;
        }finally{listener.dispose();clearTimeout(timeout);this.controllers.delete(controller);}
      });
      if(installed){const choice=await this.notify('视觉学习已更新到 '+update.version+'，代码与学习记录已保留。保存文件后重载窗口生效。','重载窗口','稍后');if(choice==='重载窗口')await vscode.commands.executeCommand('workbench.action.reloadWindow');}
      return installed;
    }finally{try{await vscode.workspace.fs.delete(file);}catch{}}
  }
  dispose(){clearTimeout(this.timer);for(const controller of this.controllers)controller.abort();this.controllers.clear();}
}
module.exports={Updater};
