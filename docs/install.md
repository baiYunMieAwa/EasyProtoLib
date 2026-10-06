安装 EasyProtoLib
================

### 安装前须知
1. 本项目**不活跃**。由于作者学业繁忙，本项目目前处于半停更状态，且作者很可能无法及时处理 Issues 和 PR 等。
2. **本库还处于 WIP 阶段，API 可能会频繁变化，并且很可能不向下兼容。**
3. 虽然理论上跨平台，但本库尚未在`Linux`、`macOS`、`Windows 7`等系统上进行充分测试，目前的测试仅在`Windows 10`上进行。
4. 本协议库目前**不提供网络层**。也就是说，您需要有`socket`或其他网络基础才能相对顺畅的使用本库。
5. 本库最低 Python 版本要求为 3.10，无法保证本库在 3.9 及以下版本的可用性和稳定性。

> 如果你真的接受上述所有局限、依然打算使用本库，那么我们就开始吧:3。

---

## 安装

### 下载并安装

安装本库的方法和其他库的方法无异，就是使用 pip 安装。

#### Windows

在`cmd`或`powershell`中输入以下命令，安装本库：
```cmd
python -m pip install easyprotolib
```

输入以下命令，检查安装是否成功：
```cmd
python -m pip show easyprotolib
```
如果显示了本库的信息，就说明安装成功了。如果显示`WARNING`，则安装失败。

#### Linux & macOS


在`bash`或其他 shell 中输入以下命令，安装本库：
```shell
python3 -m pip install easyprotolib
```

输入以下命令，检查安装是否成功：
```shell
python3 -m pip show easyprotolib
```
如果显示了本库的信息，就说明安装成功了。如果显示`WARNING`，则安装失败。

### 导入

使用 `import easyprotolib` 以导入本库。  
更好的做法是，使用 `import easyprotolib as ep` ，把本库的名称简写为 `ep` 。  
示例：
```python
import easyprotolib as ep

print("Hello, EasyProtoLib! ")
print(f"Version: {ep.__version__}")
```

---

**感谢您选择 EasyProtoLib ! ✧\*｡٩(ˊᗜˋ\*)و✧\*｡**
