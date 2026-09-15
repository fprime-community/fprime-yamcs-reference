# FprimeYamcsReference F´ project

This is a basic project that shows F Prime/YAMCS integration. It has two key features:

1. It uses `Drv.Udp` as the communication driver
2. It has YAMCS and F Prime/YAMCS packages in `requirements.txt`
3. It encrypts the space link with SDLS AES-256-GCM (`Svc.ComCcsdsSdls` with `Svc.Ccsds.AesGcmEncryptor`/`AesGcmDecryptor`)

## Building

Install the tooling into a virtual environment first: `python3 -m venv fprime-venv && . fprime-venv/bin/activate &&
pip install -r requirements.txt`. `requirements.txt` includes the framework's `lib/fprime/requirements.txt`, which
carries `fprime-gds`, `fprime-yamcs`, `yamcs-client`, and `fprime-xtce`.

The AES-GCM components require OpenSSL 3.0 or newer. If it is not the system default, point CMake at it with
`-DOPENSSL_ROOT_DIR=/path/to/openssl` when generating.

Building is done in the standard F Prime way:

1. `fprime-util generate`
2. `fprime-util build`

## Running

The deployment and YAMCS share one 32-byte AES-256 key, read by `Svc.Ccsds.SdlsFileKeyManager` on the flight side
and by YAMCS's `SecurityAssociationAes256Gcm128` on the ground side. Generate one at the project root (it is
`.gitignore`d; never commit real key material):

```sh
head -c 32 /dev/urandom > sdls.key
```

Then run `fprime-yamcs` and open `http://localhost:8090` in your browser! `fprime-gds.yml` passes
`--communication-selection udp`, so the deployment's `Drv.Udp` talks to YAMCS directly instead of through the
`fprime-yamcs-comm` bridge that `fprime-yamcs` starts by default for TCP/UART deployments, and
`--yamcs-sdls-key-file sdls.key`, which configures YAMCS to decrypt TM/encrypt TC on SPI 1, and
`--application-arguments -p 50000 -a 0.0.0.0 -k sdls.key`, which launches the deployment with the same key.
Running the binary by hand: `./FprimeYamcsReference_YamcsDeployment -a 127.0.0.1 -p 50000 -k sdls.key`.