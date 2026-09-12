"""Lecture HTTP partielle d'archives publiques ; jamais de téléchargement intégral implicite."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import urllib.request
import zipfile

SOURCES = {
    'nist': ('https://data.nist.gov/od/ds/ark:/88434/mds2-2233/LayerCamera_PNGs.zip', 8274867403),
    'aalto': ('https://zenodo.org/api/records/14996806/files/Original%20Images%20and%20Manual%20Labels.zip/content', 437503887),
}


class RemoteZip(io.RawIOBase):
    def __init__(self, url, size, budget=180_000_000):
        self.url, self.size, self.pos = url, size, 0
        self.received, self.budget = 0, budget

    def seekable(self):
        return True

    def readable(self):
        return True

    def seek(self, offset, whence=0):
        self.pos = offset if whence == 0 else (self.pos if whence == 1 else self.size) + offset
        if self.pos < 0:
            raise ValueError('Position négative')
        return self.pos

    def tell(self):
        return self.pos

    def read(self, size=-1):
        size = self.size-self.pos if size < 0 else min(size, self.size-self.pos)
        if size <= 0:
            return b''
        if size > self.budget-self.received:
            raise ValueError('Budget réseau de 180 Mo dépassé ; arrêter ou choisir moins de couches.')
        end = self.pos+size-1
        request = urllib.request.Request(self.url, headers={
            'User-Agent': 'LPBF-Inspector-Research/0.1', 'Range': f'bytes={self.pos}-{end}'})
        with urllib.request.urlopen(request, timeout=30) as response:
            expected = f'bytes {self.pos}-{end}/{self.size}'
            if response.status != 206 or response.headers.get('Content-Range') != expected:
                raise ValueError('Le serveur ne respecte pas la lecture partielle. Téléchargement arrêté.')
            data = response.read(size+1)
        if len(data) != size:
            raise ValueError('Réponse partielle tronquée ou trop longue')
        self.pos += len(data)
        self.received += len(data)
        return data


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('source', choices=SOURCES)
    parser.add_argument('--sample', action='store_true')
    parser.add_argument('--count', type=int, default=20, help='Nombre de JPEG Aalto, de 1 à 20')
    args = parser.parse_args()
    if not 1 <= args.count <= 20:
        parser.error('--count doit être compris entre 1 et 20')
    root = Path(__file__).resolve().parent
    remote = RemoteZip(*SOURCES[args.source])
    with zipfile.ZipFile(remote) as archive:
        infos = archive.infolist()
        listing = [{'name': i.filename, 'compressed_bytes': i.compress_size, 'bytes': i.file_size} for i in infos]
        (root/f'{args.source}_archive_index.json').write_text(json.dumps(listing, ensure_ascii=False, indent=2), encoding='utf-8')
        print('Entrées', len(infos), 'Octets du sommaire reçus', remote.received, flush=True)
        for info in infos[:35]:
            print(info.filename, info.file_size, flush=True)
        if args.sample:
            selected = []
            for info in infos:
                match = re.fullmatch(r'([AB])(\d{4})a\.png', Path(info.filename).name, re.I)
                if args.source == 'nist' and match and 120 <= int(match[2]) <= 129:
                    selected.append(info)
            if args.source == 'aalto':
                selected = [i for i in infos if '/PB/' in i.filename and i.filename.lower().endswith('.jpg')][:args.count]
                stems = {Path(i.filename).stem for i in selected}
                selected += [i for i in infos if '/PB_label/' in i.filename and Path(i.filename).stem in stems and i.filename.lower().endswith('.xml')]
            dest = root.parent/'datasets'/f'{args.source}_sample'
            dest.mkdir(parents=True, exist_ok=True)
            downloaded = []
            for info in selected:
                if info.file_size > 50_000_000:
                    raise ValueError('Entrée décompressée trop grande pour un échantillon')
                target = dest/Path(info.filename).name
                if target.exists():
                    print('Déjà présent', target.name, flush=True)
                    downloaded.append({'archive_path': info.filename, 'file': target.name,
                                       'sha256': hashlib.sha256(target.read_bytes()).hexdigest()})
                    continue
                data = archive.read(info)  # CRC du ZIP vérifié par zipfile.
                target.write_bytes(data)
                downloaded.append({'archive_path': info.filename, 'file': target.name,
                                   'sha256': hashlib.sha256(data).hexdigest()})
                print('Enregistré', target.name, len(data), 'octets', flush=True)
            (dest/'provenance.json').write_text(json.dumps({'archive_url': remote.url,
                'selection': 'Couches 120 à 129, éclairage a, deux étapes' if args.source == 'nist' else f'{args.count} premières images PB et annotations correspondantes si disponibles',
                'files': downloaded}, ensure_ascii=False, indent=2), encoding='utf-8')
            print('Échantillon', len(selected), 'images ; réseau', remote.received, 'octets', flush=True)


if __name__ == '__main__':
    main()
