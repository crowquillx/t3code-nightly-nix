{
  appimageTools,
  fetchurl,
  lib,
  makeBinaryWrapper,
  symlinkJoin,
}:
let
  pin = builtins.fromJSON (builtins.readFile ./pin.json);
  pname = "t3code-nightly";
  inherit (pin) version;
  src = fetchurl {
    url = "https://github.com/pingdotgg/t3code/releases/download/v${version}/T3-Code-${version}-x86_64.AppImage";
    hash = pin.hash;
  };
  contents = appimageTools.extract {
    inherit pname version src;
  };
  wrapped = appimageTools.wrapType2 {
    inherit pname version src;

    extraInstallCommands = ''
      install -Dm444 \
        ${contents}/t3code.desktop \
        "$out/share/applications/t3code-nightly.desktop"
      substituteInPlace "$out/share/applications/t3code-nightly.desktop" \
        --replace-fail "Name=T3 Code" "Name=T3 Code Nightly" \
        --replace-fail "Exec=AppRun" "Exec=t3code-nightly"
      cp -r ${contents}/usr/share/icons "$out/share/"
    '';

    meta = {
      description = "Nightly desktop control surface for coding agents";
      homepage = "https://t3.codes";
      downloadPage = "https://github.com/pingdotgg/t3code/releases/tag/v${version}";
      changelog = "https://github.com/pingdotgg/t3code/releases/tag/v${version}";
      license = lib.licenses.mit;
      mainProgram = pname;
      platforms = [ "x86_64-linux" ];
      sourceProvenance = [ lib.sourceTypes.binaryNativeCode ];
    };
  };
in
symlinkJoin {
  inherit pname version;
  paths = [ wrapped ];
  nativeBuildInputs = [ makeBinaryWrapper ];

  postBuild = ''
    wrapProgram "$out/bin/t3code-nightly" \
      --add-flags "--no-sandbox --password-store=gnome-libsecret"
  '';

  passthru = {
    inherit contents src wrapped;
  };

  inherit (wrapped) meta;
}
