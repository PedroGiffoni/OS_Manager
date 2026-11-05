from pathlib import Path
import shutil
from PIL import Image, ImageDraw, ImageFont

root = Path(__file__).resolve().parents[1]
source = root / 'frontend' / 'test-results'
out = root / 'docs' / 'media'
out.mkdir(parents=True, exist_ok=True)
shots = {
 'dashboard-light.png': 'sebrae-dashboard-claro.png',
 'dashboard-dark.png': 'sebrae-dashboard-escuro.png',
 'kanban.png': 'kanban-desktop.png',
 'reports.png': 'analise-cards-desktop.png',
 'card-analysis.png': 'analise-card-desktop.png',
 'mobile-light.png': 'sebrae-dashboard-mobile-claro.png',
 'mobile-dark.png': 'sebrae-dashboard-mobile-escuro.png',
 'hours-alert.png': 'erro-horas-modal.png',
}
for target, original in shots.items():
    with Image.open(source / original) as im:
        im.save(out / target, optimize=True)
font_path = Path('C:/Windows/Fonts/segoeuib.ttf')
font = ImageFont.truetype(str(font_path), 19)
small = ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf', 13)
frames = []
chapters = [
 ('dashboard-light.png', '01 / Visão geral', 'Indicadores reais de demandas e entregas'),
 ('kanban.png', '02 / Kanban', 'Cada atividade no seu estágio de execução'),
 ('reports.png', '03 / Relatórios', 'Filtros e análise operacional dos cards'),
 ('card-analysis.png', '04 / Histórico do card', 'Permanências, ciclos e aprovações'),
 ('dashboard-dark.png', '05 / Tema escuro', 'A mesma operação, com outra preferência visual'),
]
for index, (name, title, subtitle) in enumerate(chapters):
    with Image.open(out / name) as im:
        scaled = im.convert('RGB').resize((1000, round(im.height * 1000 / im.width)), Image.Resampling.LANCZOS)
    # A viewport crop keeps screenshot text readable; the static gallery preserves the full captures.
    for step in range(8):
        canvas = Image.new('RGB', (1040, 700), '#091b43')
        draw = ImageDraw.Draw(canvas)
        draw.text((22, 13), 'GESTÃO DE DEMANDAS', font=font, fill='white')
        draw.text((22, 43), title + '  ·  ' + subtitle, font=small, fill='#c7dcff')
        y = round(min(max(0, scaled.height - 590), 135) * step / 7)
        crop = scaled.crop((0, y, 1000, min(y + 590, scaled.height)))
        canvas.paste(crop, (20, 79))
        draw.rectangle((20, 682, 1020, 686), fill='#263c66')
        draw.rectangle((20, 682, round(20 + 1000 * ((index * 8 + step + 1) / 40)), 686), fill='#5edcff')
        frames.append(canvas.quantize(colors=128))
frames[0].save(out / 'product-tour.gif', save_all=True, append_images=frames[1:], duration=[1800 if i % 8 == 0 else 160 for i in range(len(frames))], loop=0, optimize=True)
print('Media generated from actual E2E screenshots:')
for path in out.iterdir():
    print(path.name, path.stat().st_size)
