# インストール

[Releases](https://github.com/kotek-7/sts-studio/releases/latest)からOSに合うバイナリを取得します。Intel/AMDのPCはx86_64、Apple siliconのMacはarm64です。実行ファイルの隣にあるライブラリも必要なので、フォルダー全体を展開してください。sourceアーカイブは自分でビルドする場合に使います。

## Ubuntu

```sh
sudo apt install ./sts-studio_<version>_amd64.deb
sts-studio-gui --demo
sts-studio --demo scan
```

debは`/opt/sts-studio`に配置され、アプリ一覧に追加されます。削除は`sudo apt remove sts-studio`です。

tar.gz版は展開して`./gui/sts-studio-gui`を実行します。必要なシステムライブラリは[英語の導入手順](INSTALL.md#ubuntu)に記載しています。

ポートへのアクセスが拒否された場合は、`ls -l /dev/ttyUSB0`と`id`で権限を確認します。Ubuntuでは通常dialoutグループが必要です。`sudo usermod -aG dialout "$USER"`で追加し、一度ログアウトして入り直してください。アプリ自体をrootで起動する必要はありません。

## Windows

ZIP全体を展開し、`gui\sts-studio-gui.exe`を起動します。CLIは展開先でPowerShellを開いて実行します。

```powershell
.\cli\sts-studio.exe --demo scan
```

未署名のため、Windowsが発行元不明やSmartScreenの警告を表示する場合があります。このリポジトリのReleaseから取得したこととチェックサムを確認してから実行を判断してください。管理されたPCでは未署名アプリを実行できない場合があります。USBアダプターによってはメーカーのドライバーが必要です。

## macOS

ZIPを展開して`STS Studio.app`を開きます。CLIや文書を一緒に保管する場合は、展開フォルダー全体をApplicationsへ移動できます。

Developer ID署名・公証はしていません。起動が拒否された場合は取得元とチェックサムを確認し、システム設定の「プライバシーとセキュリティ」でこのアプリの「このまま開く」を選びます。Gatekeeper全体を無効化する必要はありません。管理されたMacでは例外を許可できない場合があります。

CLIはターミナルで`./cli/sts-studio --demo scan`を実行します。ポート名は通常`/dev/cu.*`です。

## チェックサムと更新

Releaseの`SHA256SUMS.txt`を取得します。Linuxは`sha256sum <ファイル>`、macOSは`shasum -a 256 <ファイル>`、PowerShellは`Get-FileHash <ファイル> -Algorithm SHA256`で計算し、該当するファイル名の値と比較します。チェックサムは破損・取り違えの検出用で、発行元の署名ではありません。

debは新しいファイルをaptでインストールします。ZIP・tar.gzは新しいフォルダーへ展開し、古いライブラリを混ぜないでください。記録データと`.xdat`のバックアップはアプリのフォルダー外へ保存してください。
