# Kotra-KB-Light

适合 KDE Plasma 的 PySide6 原生界面，跟随系统 Qt 样式与配色。
包含环境光实时读数、阶梯曲线图、可编辑档位、JSON 配置和手动亮度滑块。
不能没有键盘自动亮度！！！

## 启动

本机已安装 PySide6。在终端执行：

```sh
cd /home/aotra/Documents/code/Kotra-KB-Light
python3 gui.py
```

无需 sudo 启动 GUI。程序通过 UPower D-Bus 请求调光，而非放宽 sysfs 权限。
如果系统拒绝请求，界面会显示错误；不要以 root 运行整个 GUI。

1. 初次启动只显示读数，不改变灯光，也不请求键盘权限。
2. 修改表格中的起始 lux 与亮度；每个档位包含左端、不包含下一档的左端。
3. 使用「曲线查询」检查任意 lux 的目标；点击「保存配置」另存为 JSON。
4. 「自动调节 / 常亮」是互斥的两态选择，初始均未激活。
5. 点击「自动调节」会同时发起全局按键检测授权；等待授权时不改变灯光。授权完成后按键立即亮起、保持 1 秒、4 秒渐暗。取消授权则停止接管。
6. 点击「常亮」立即按环境光曲线控制，不需要按键检测；环境足够亮仍关闭。
7. 手动滑块配合「应用手动亮度」直接设置固定亮度，并停止曲线控制。

独立的「仅预览」复选框和「启用全局按键检测」按钮已移除。
编辑曲线会停止自动调节，修改验证通过后可重新开启。
关闭窗口会收起到系统托盘，继续调光并保留未保存的编辑。托盘菜单「退出并恢复亮度」才会退出并尝试恢复接管前亮度；检测到外部改动时不覆盖它。
编辑配置会暂停接管并保留当前亮度，选择一个模式可重新开始。
支持托盘常驻；尚未配置开机自动启动。
启动时载入内置预设；自定义配置用「打开配置」加载。

## 倒 U 预设

文件：`presets/inverted-u.json`

| 起始 lux | 键盘亮度 / 255 |
|---:|---:|
| 0 | 13 |
| 2 | 26 |
| 10 | 51 |
| 30 | 89 |
| 80 | 64 |
| 150 | 26 |
| 250 | 0 |

全黑时微亮、中间较亮、明亮环境关闭。这是可调整的初始策略，不是苹果原厂曲线。
亮度数值统一为 0–255，运行时按实际设备最大值缩放。
曲线图横轴为 log(1+lux)，以便同时观察低光与明亮区间；不进行曲线插值。
环境光采用 3 秒指数平滑、10% 边界切换幅度和 2 秒换挡等待。GUI 按键亮灯绕过亮度渐入，每 50ms 更新渐暗；系统负载及 D-Bus 延迟仍会影响实际响应时间。
切换幅度和换挡等待可在 GUI 修改。GUI 自动模式会持续接管亮度；需要手动固定时使用界面的手动应用按钮。命令行保留外部手动调光后让步 60 秒及渐入行为。
曲线查询和图上圆点表示静态目标，实时自动值还受平滑与切换幅度影响。

## 命令行

```sh
python3 kbd_auto.py --dry-run --samples 10
python3 kbd_auto.py --config custom.json --dry-run --samples 10
sudo python3 kbd_auto.py --config custom.json
```

命令行使用 sysfs 写入，实际控制仍需相应权限。Ctrl+C 会尝试恢复原亮度。
GUI 与命令行共享环境光曲线；按键计时与常亮开关目前仅在 GUI 提供。不要同时运行 GUI 自动控制与旧 systemd 服务。
GUI 有单实例锁，但无法阻止其他调光工具或命令行实例。

## 可选：安装命令行后台服务

先停止其他自动调光程序并完成前台验证，再执行：

```sh
sudo install -d -m 755 /usr/local/lib/Kotra-KB-Light/presets
sudo install -m 644 kbd_auto.py curve.py /usr/local/lib/Kotra-KB-Light/
sudo install -m 644 presets/inverted-u.json /usr/local/lib/Kotra-KB-Light/presets/
sudo install -m 644 Kotra-KB-Light.service /etc/systemd/system/Kotra-KB-Light.service
sudo systemctl daemon-reload
sudo systemctl enable --now Kotra-KB-Light.service
```

服务默认加载倒 U 预设。自定义配置需自行复制到服务可读取位置，并通过
`systemctl edit` 设置 ExecStart 的 `--config` 参数；GUI 保存文件不会自动更新后台服务。

## 验证范围

本机检测到 M1 MacBook Air，`aop-sensors-als` 的 `in_illuminance_input`
提供实时 lux，键盘背光最大值为 255。
18 项测试覆盖曲线边界、配置读写、切换幅度/延迟、外部手动调整、模拟硬件写入恢复、GUI 编辑校验、权限失败、按键计时/重新触发及亮处熄灯。
已完成离屏 GUI 渲染与真实环境光读取。自动测试不代表真实灯光写入或合盖行为已验证。
目前不包含闲置熄灯、合盖检测、传感器校准或内核驱动安装。

```sh
QT_QPA_PLATFORM=offscreen python3 -m unittest discover -v
```

## 接口文档

- https://upower.pages.freedesktop.org/upower.freedesktop.org/docs/KbdBacklight.html
- https://doc.qt.io/qtforpython-6/PySide6/QtDBus/QDBusInterface.html
- https://asahilinux.org/docs/platform/feature-support/m1/

## 按键检测权限与更新

需要系统提供 `pkexec` 和桌面认证代理，授权取消或检测助手退出时，按键自动模式停止并尝试恢复亮度。助手随程序真正退出而结束；不修改 input 组权限，不安装持久 root 服务。当前仅支持内置键盘，外接键盘不会触发。

更新 Python 文件不会改变已经打开的旧窗口。先保存配置、从托盘退出旧程序（旧版无托盘时关闭窗口），再运行 `python3 gui.py` 加载新版。全局按键读取与实际灯光时序仍需桌面授权后实测；自动测试使用模拟键盘时间和模拟背光。

## 托盘与终端释放

`python3 gui.py` 默认启动独立后台进程并立即返回终端；关闭终端不影响程序。
窗口关闭按钮只隐藏窗口，托盘可以打开设置、选择自动或常亮模式或真正退出。
没有可用系统托盘时回退为普通窗口，关闭即退出。

```sh
# 直接进入托盘，不显示设置窗口
python3 gui.py --hidden

# 排查问题时保留前台进程和日志输出
python3 gui.py --foreground
```

后台日志在 `${XDG_STATE_HOME:-~/.local/state}/Kotra-KB-Light/gui.log`。
启动提示表示后台进程已创建，若窗口/托盘未出现，请查看日志。
重复启动受单实例锁限制，使用现有托盘打开设置。首次启动不接管灯光，需自行选择自动调节或常亮。

百分比和持续时间位于主界面「换档配置」按钮的弹出菜单中，修改仍随 JSON 曲线一起保存。

## 更名后的服务迁移

`Kotra-KB-Light.service` 仍是可选的命令行环境光调节服务，不启动 GUI、托盘或按键计时。使用桌面程序时不要同时启用此服务。其安装路径为 `/usr/local/lib/Kotra-KB-Light`，与源码目录分开；只移动源码目录不会移动已安装程序。

若此前安装过旧版 `m1-kbd-auto.service`，先执行 `sudo systemctl disable --now m1-kbd-auto.service`，再按上面的安装步骤复制新版文件并加载新服务。若没有安装过旧服务，无需执行此步骤。

桌面启动器已改为新的源码目录；此前复制到应用菜单或自启动目录的 `.desktop` 文件，也需要替换为新版。GUI 的日志目录及单实例锁保留旧内部标识以兼容已有实例，这不影响程序显示名称或启动路径。

## 中文 / English 与关于页面

窗口右上角的「English / 中文」按钮可立即切换界面语言，包括曲线坐标、档位配置、运行状态和托盘菜单，不影响当前调光模式或未保存的编辑。语言选择目前仅对本次运行有效。

「关于 / About」可从窗口及托盘打开，注明作者 AotraWong 和 GitHub 仓库网址。页面本身离线可读，外部链接仅在点击时打开。

Use the **English / 中文** button to switch languages without restarting or interrupting brightness control. Open **About** from the window or system tray for author AotraWong and the GitHub repository URL. No logs are uploaded automatically. Language selection applies to the current session.

终端启动回显、命令行调光日志及按键助手错误提示采用中英双语；原始系统错误保持原样。助手的 READY/KEY 是内部通信标记，不作翻译。

主界面仅保留曲线图与运行控制。点击「曲线配置 / Curve configuration」打开二级大面板，集中载入预设、打开/保存配置、编辑/添加/删除档位、换档配置和曲线查询；关闭面板不丢弃当前编辑。

日志目录已随应用更名为 `Kotra-KB-Light`；旧 `m1-kbd-auto/gui.log` 保留原位，不自动移动或删除。下次启动后写入新目录。

关于页列明项目许可证 GNU GPL v3，以及 PySide6 / Qt 6、Python 标准库、UPower / D-Bus 和 polkit（pkexec）；第三方组件各自的许可证不受项目许可声明影响。
