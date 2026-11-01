# 開発時の検査

`uv run --locked python tools/check.py`で整形・lint・型・生成仕様書との整合・テストを確認します。

テストはVirtualLink、Qtの操作イベント、LinuxのPTYを使います。CIでは各OSで共通テストを実行し、PTY試験だけLinuxで実行します。配布物は開発用のソースやvenvに依存しない場所でGUIデモ起動とCLIを確認します。

現在の結果は[GitHub Actions](https://github.com/kotek-7/sts-studio/actions/workflows/check.yml)を参照してください。テストの実行には実機を使いません。
