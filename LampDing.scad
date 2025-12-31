// =========================
// Parameters
// =========================
diameter = 150;          // mm
thickness = 2.5;         // mm
hole_diameter = 8;       // mm
hole_count = 50;         // aantal gaten (tweakbaar)
$fn = 256;

// =========================
// Afgeleide maten
// =========================
R = diameter / 2;
r_inner = R - thickness;
hc = ceil(hole_count * 2.323);

// =========================
// Dome (halve bol, hol)
// =========================
module dome_shell() {
    difference() {
        sphere(r = R);
        sphere(r = r_inner);
        translate([0,0,-R])
            cube([2*R,2*R,2*R], center=true);
    }
}

// =========================
// Radiaal georiënteerd gat
// =========================
module radial_hole(theta, phi) {
    rotate([0, 0, phi])
    rotate([0, theta, 0])
    translate([0, 0, r_inner])
        cylinder(
            d = hole_diameter,
            h = thickness*2,
            center = true
        );
    
        x = r_inner * sin(theta) * cos(phi);
        y = r_inner * sin(theta) * sin(phi);
        zc = r_inner* cos(theta);

        echo(
            str(
                x, ",",
                y, ",",
                zc, ",",
                theta, ",",
                phi % 360
            )
        );
}

// =========================
// Fibonacci-verdeling
// =========================
module holes_fibonacci() {
    golden = (1 + sqrt(5)) / 2;

    for (i = [0 : hc - 1]) {
        z = 1 - 2 * (i + 0.5) / hc;
        theta = acos(z);
        phi = 360 * i / golden;

        // alleen bovenste hemisfeer
        if (theta < 90-hole_diameter)
            radial_hole(theta, phi);
    }
}

echo("x,y,z,theta_deg,phi_deg");

// =========================
// Eindmodel
// =========================
difference() {
    dome_shell();
    holes_fibonacci();
}

// =========================
// Gatenteller
// =========================
function valid_holes() =
    [
        for (i = [0 : hc - 1])
            let(
                z = 1 - 2 * (i + 0.5) / hc,
                theta = acos(z)
            )
            if (theta < 90 - hole_diameter)
                i
    ];

echo("Aantal gaten:", len(valid_holes()));

