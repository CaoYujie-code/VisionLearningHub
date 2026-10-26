from pathlib import Path
import hashlib
import json
import urllib.request

root=Path(__file__).resolve().parents[1]/'content/engineering'
root.mkdir(parents=True,exist_ok=True)
specs=[
    ('coins.png','f8d773fc9cfa6f4d8e5942dc34d0a0788fcaed2a4fefbbed0aef5398d7ef4cba','Brooklyn Museum Collection，经 scikit-image 分发','No known copyright restrictions；上游未标为 CC0。','https://www.brooklynmuseum.org/opencollection/archives/image/51611'),
    ('brick.png','7966caf324f6ba843118d98f7a07746d22f6a343430add0233eca5f6eaaa8fcf','CC0Textures / ambientCG，经 scikit-image 变换分发','CC0-1.0','https://ambientcg.com/'),
    ('gravel.png','c48615b451bf1e606fbd72c0aa9f8cc0f068ab7111ef7d93bb9b0f2586440c12','CC0Textures / ambientCG，经 scikit-image 裁剪分发','CC0-1.0','https://ambientcg.com/'),
]
assets=[]
for name,digest,author,license,origin in specs:
    url='https://raw.githubusercontent.com/scikit-image/scikit-image/v0.25.2/skimage/data/'+name
    raw=urllib.request.urlopen(url,timeout=30).read()
    assert hashlib.sha256(raw).hexdigest()==digest,name
    (root/name).write_bytes(raw)
    assets.append(dict(file=name,sha256=digest,download=url,credit=author,license=license,origin=origin,license_evidence='https://github.com/scikit-image/scikit-image/blob/v0.25.2/skimage/data/_fetchers.py',checked_at='2026-10-26'))
(root/'sources.json').write_text(json.dumps(assets,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(root/'NOTICE.md').write_text('''# 工程图片来源

本目录保留上游原始PNG，固定至 scikit-image v0.25.2，并记录SHA-256。学习运行不需要联网，不依赖scikit-image包。

- coins.png：Brooklyn Museum Collection；scikit-image 声明“无已知版权限制”，并非明确CC0授权。
- brick.png、gravel.png：原始纹理来自CC0Textures（现ambientCG），上游声明CC0；scikit-image已做裁剪、缩放等处理。
- 下载地址、原始来源和许可依据见 sources.json。CC0说明：https://creativecommons.org/publicdomain/zero/1.0/

项目产生的缺陷、光照、透视、运动序列和空场景是程序生成的教学变体，不能作为真实工厂缺陷、真实视频采集或独立现场测试集。变体来自少量原图，通关只验证本课程协议，不证明现场泛化能力。
''',encoding='utf-8')
print(json.dumps([{'file':a['file'],'sha256':a['sha256']} for a in assets]))
