"""
Generate a sample restaurant menu PDF for the Krid AI media library.
Run once:  python media/generate_menu_pdf.py
"""

from fpdf import FPDF


class MenuPDF(FPDF):
    """Custom PDF for a restaurant menu."""

    def header(self):
        self.set_font("Helvetica", "B", 28)
        self.set_text_color(139, 69, 19)  
        self.cell(0, 18, "La Maison Elegante", align="C", new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "I", 12)
        self.set_text_color(100, 100, 100)
        self.cell(0, 8, "Fine Dining & Cocktails", align="C", new_x="LMARGIN", new_y="NEXT")
        self.line(20, self.get_y() + 2, 190, self.get_y() + 2)
        self.ln(8)

    def footer(self):
        self.set_y(-20)
        self.set_font("Helvetica", "I", 9)
        self.set_text_color(140, 140, 140)
        self.cell(0, 10, "La Maison Elegante  |  123 Gourmet Avenue  |  Tel: (555) 987-6543", align="C")

    def section_title(self, title: str):
        self.set_font("Helvetica", "B", 16)
        self.set_text_color(139, 69, 19)
        self.cell(0, 12, title, new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(200, 170, 130)
        self.line(self.get_x(), self.get_y(), self.get_x() + 60, self.get_y())
        self.ln(4)

    def menu_item(self, name: str, description: str, price: str):
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(40, 40, 40)
        
        self.cell(150, 6, name)
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(139, 69, 19)
        self.cell(0, 6, price, align="R", new_x="LMARGIN", new_y="NEXT")
        
        self.set_font("Helvetica", "", 9)
        self.set_text_color(100, 100, 100)
        self.multi_cell(0, 5, description)
        self.ln(3)


def generate_menu():
    pdf = MenuPDF()
    pdf.set_auto_page_break(auto=True, margin=25)
    pdf.add_page()

    
    pdf.section_title("Starters")
    pdf.menu_item(
        "Truffle Burrata",
        "Creamy burrata with black truffle shavings, heirloom tomatoes, and aged balsamic drizzle.",
        "$18",
    )
    pdf.menu_item(
        "Seared Tuna Tataki",
        "Sesame-crusted yellowfin tuna, pickled ginger, ponzu sauce, micro greens.",
        "$22",
    )
    pdf.menu_item(
        "French Onion Soup",
        "Caramelized onion broth, gruyere crouton, fresh thyme.",
        "$14",
    )
    pdf.menu_item(
        "Lobster Bisque",
        "Velvety bisque with brandy cream, lobster claw garnish, chive oil.",
        "$19",
    )

    pdf.ln(4)

    
    pdf.section_title("Main Courses")
    pdf.menu_item(
        "Wagyu Beef Tenderloin",
        "A5 grade wagyu, truffle pomme puree, red wine jus, roasted baby vegetables.",
        "$65",
    )
    pdf.menu_item(
        "Pan-Seared Chilean Sea Bass",
        "Miso-glazed sea bass, coconut jasmine rice, bok choy, lemongrass broth.",
        "$48",
    )
    pdf.menu_item(
        "Herb-Crusted Rack of Lamb",
        "New Zealand lamb, rosemary crust, dauphinoise potatoes, mint gremolata.",
        "$52",
    )
    pdf.menu_item(
        "Wild Mushroom Risotto",
        "Arborio rice, porcini and chanterelle mushrooms, parmesan foam, truffle oil. (V)",
        "$32",
    )
    pdf.menu_item(
        "Duck Confit",
        "Slow-cooked duck leg, cherry compote, roasted root vegetables, port reduction.",
        "$42",
    )

    pdf.ln(4)

    
    pdf.section_title("Desserts")
    pdf.menu_item(
        "Chocolate Lava Cake",
        "Valrhona dark chocolate, vanilla bean ice cream, gold leaf, raspberry coulis.",
        "$16",
    )
    pdf.menu_item(
        "Creme Brulee Trio",
        "Classic vanilla, lavender honey, and espresso creme brulee with caramelized sugar.",
        "$14",
    )
    pdf.menu_item(
        "Tiramisu",
        "Mascarpone cream, espresso-soaked ladyfingers, cocoa dust, amaretto drizzle.",
        "$15",
    )

    pdf.ln(4)

    
    pdf.section_title("Beverages")
    pdf.menu_item(
        "Signature Old Fashioned",
        "Woodford Reserve bourbon, demerara syrup, Angostura bitters, flamed orange peel.",
        "$18",
    )
    pdf.menu_item(
        "Espresso Martini",
        "Grey Goose vodka, Kahlua, freshly pulled espresso, vanilla syrup.",
        "$16",
    )
    pdf.menu_item(
        "Sommelier's Wine Pairing",
        "Three-course wine pairing selected by our sommelier to complement your meal.",
        "$45",
    )

    output_path = "media/restaurant_menu.pdf"
    pdf.output(output_path)
    print(f"[PDF] Menu generated: {output_path}")


if __name__ == "__main__":
    generate_menu()
