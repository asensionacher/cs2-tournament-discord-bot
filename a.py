from PIL import Image, ImageDraw, ImageFont

# Crear una imagen base
width, height = 900, 450
img = Image.new('RGB', (width, height), color=(36, 45, 60))
draw = ImageDraw.Draw(img)

# Cargar fuentes
font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
font_bold_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
font = ImageFont.truetype(font_path, 16)
font_bold = ImageFont.truetype(font_bold_path, 18)

# Colores
white = (255, 255, 255)
gray = (180, 180, 180)
green = (0, 255, 0)
red = (255, 64, 64)
blue = (100, 149, 237)

# Datos de ejemplo
teams = [
    {
        "name": "Iberian Soul",
        "color": blue,
        "players": [
            ("Alejandro 'alex' Masanet", "50-24", "+26", "117.9", "85.4%", "1.82"),
            ("Renato 'stadodo' Gonçalves", "32-24", "+8", "75.8", "80.5%", "1.24"),
            ("Pere 'sausol' Solsona Saumell", "31-29", "+2", "79.9", "85.4%", "1.16"),
            ("Alejandro 'mopoz' Fernández-Quejo Cano", "24-25", "-1", "63.4", "75.6%", "0.97"),
            ("David 'dav1g' Granado Bermudo", "20-28", "-8", "64.7", "80.5%", "0.93")
        ]
    },
    {
        "name": "CYBERSHOKE",
        "color": blue,
        "players": [
            ("Ilya 'FenomeN' Kolodko", "31-29", "+2", "80.9", "70.7%", "1.08"),
            ("Denis 'notineki' Kalachev", "31-32", "-1", "81.8", "68.3%", "1.00"),
            ("Aleksandr 'glowing' Matsievich", "27-34", "-7", "77.9", "78.0%", "0.98"),
            ("Daniil 'lov1kus' Nikitin", "20-32", "-12", "63.2", "61.0%", "0.83"),
            ("David 'b1lx1' Stepanyants", "19-32", "-13", "50.1", "68.3%", "0.75")
        ]
    }
]

# Dibujar contenido
# # Reutilizar fuentes y colores
column_titles = ["K-D", "+/-", "ADR", "KAST", "Rating"]
column_x = [520, 590, 640, 700, 760]

# Redibujar con mejor centrado
y_offset = 20
for team in teams:
    draw.text((width // 2 - draw.textlength(team["name"], font=font_bold) // 2, y_offset),
              team["name"], font=font_bold, fill=team["color"])
    y_offset += 30

    # Column titles
    draw.text((150, y_offset), "Player", font=font, fill=gray)
    for title, x in zip(column_titles, column_x):
        draw.text((x, y_offset), title, font=font, fill=gray)
    y_offset += 25

    for player in team["players"]:
        draw.text((20, y_offset), player[0], font=font, fill=white)

        for i, (stat, x) in enumerate(zip(player[1:], column_x)):
            color = white
            if i == 1:  # +/- column
                color = green if "+" in stat else red
            draw.text((x, y_offset), stat, font=font, fill=color)
        y_offset += 28

    y_offset += 25

# Guardar imagen centrada
output_path_centered = "./discord_match_stats_centered.png"
img.save(output_path_centered)
output_path_centered
