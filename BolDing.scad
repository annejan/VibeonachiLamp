// =====================================================
// LED Globe – cleaned & structured
// =====================================================

/* [Geometry] */
diameter = 180;              // [50:400]
thickness_x10 = 80;          // [10:100]

/* [LED Holes] */
hole_diameter_x10 = 80;      // [20:200]
hole_count = 400;            // [50:800]

/* [Magnets – equator coupling] */
magnet_diameter_x10  = 40;   // [10:100]
magnet_thickness_x10 = 40;   // [20:60]
magnet_clearance_x10 = 1;    // [0:10]
magnet_count = 8;            // [2:16]

/* [Debug numbers] */
show_numbers = false;        // [true:false]
number_size = 4;
number_depth = 1.0;
number_offset = 0.01;
number_offset_x = 0;
number_offset_y = 7;
number_rotate = -90;

/* [Payload / wiring safe zone] */
show_payload = true;
payload_equator_radius = 30;     // max radius at equator
payload_clearance = 0;           // distance to inner wall

/* [Assembly] */
show_part = "bottom";        // ["top","bottom","both"]
split_gap_x100 = 0;          // [0:200]

$fn = 80;

// =====================================================
// Derived values (mm)
// =====================================================

thickness        = thickness_x10 / 10;
hole_diameter    = hole_diameter_x10 / 10;
magnet_diameter  = magnet_diameter_x10 / 10;
magnet_thickness = magnet_thickness_x10 / 10;
magnet_clearance = magnet_clearance_x10 / 10;
split_gap        = split_gap_x100 / 100;

R       = diameter / 2;
r_inner = R - thickness;
hc      = hole_count;

golden = (1 + sqrt(5)) / 2;

// Magnet geometry
magnet_r          = magnet_diameter / 2 + magnet_clearance;
magnet_len        = magnet_thickness + magnet_clearance * 2;
magnet_radius_pos = r_inner + thickness / 2;

// LED–magnet safety band around equator
equator_z_band = hole_diameter / 2 + magnet_r + 1;

// =====================================================
// Utility functions
// =====================================================

function sort(l) =
    len(l) <= 1 ? l :
    let(
        p     = l[0],
        less  = [ for (x = l) if (x < p) x ],
        more  = [ for (x = l) if (x > p) x ]
    )
    concat(sort(less), [p], sort(more));

function equator_led_phis(n, z_band) =
    [
        for (i = [0 : n - 1])
            let(
                z = r_inner * cos(acos(1 - 2 * (i + 0.5) / n))
            )
            if (abs(z) < z_band)
                (360 * i / golden) % 360
    ];

function gap_centers(phis) =
    let(
        p = sort(phis),
        l = len(p)
    )
    [
        for (i = [0 : l - 1])
            let(
                a = p[i],
                b = p[(i + 1) % l] + (i == l - 1 ? 360 : 0)
            )
            [b - a, (a + b) / 2 % 360]
    ];

function magnet_phis(n_leds, z_band, mcount) =
    let(
        phis = equator_led_phis(n_leds, z_band),
        gaps = gap_centers(phis),
        gs   = sort(gaps)
    )
    [
        for (i = [len(gs) - mcount : len(gs) - 1])
            gs[i][1]
    ];

// =====================================================
// Core geometry
// =====================================================

module sphere_shell() {
    difference() {
        sphere(r = R);
        sphere(r = r_inner);
    }
}

module radial_hole(theta, phi) {
    rotate([0, 0, phi])
    rotate([0, theta, 0])
    translate([0, 0, r_inner])
        cylinder(d = hole_diameter, h = thickness * 2, center = true);
}

module holes_fibonacci() {
    for (i = [0 : hc - 1]) {
        z     = 1 - 2 * (i + 0.5) / hc;
        theta = acos(z);
        phi   = 360 * i / golden;
        radial_hole(theta, phi);
    }
}

// =====================================================
// Engraved LED numbers (debug)
// =====================================================

module hole_number(i, theta, phi) {
    rotate([0, 0, phi])
    rotate([0, theta, 0])
    translate([number_offset_y, number_offset_x, r_inner + number_offset])
    rotate([180, 0, number_rotate])
        linear_extrude(height = number_depth + 2)
            text(
                str(i),
                size = number_size,
                halign = "center",
                valign = "center",
                font = "HersheySimplex"
            );
}

module hole_numbers() {
    for (i = [0 : hc - 1]) {
        z     = 1 - 2 * (i + 0.5) / hc;
        theta = acos(z);
        phi   = 360 * i / golden;
        hole_number(i, theta, phi);
    }
}

// =====================================================
// Magnet pockets (equator)
// =====================================================

module magnet_pocket(phi) {
    for (zsign = [-1, 1]) {
        rotate([0, 0, phi])
        translate([magnet_radius_pos, 0, zsign * magnet_len / 4])
        rotate([0, 0, 90])
            cylinder(r = magnet_r, h = magnet_len / 2, center = true);
    }
}

module magnet_pockets() {
    for (phi = magnet_phis(hc, equator_z_band, magnet_count))
        magnet_pocket(phi);
}

// =====================================================
// Payload / wiring keep-out (ellipsoidal)
// =====================================================

module payload_ellipsoid(equator_radius, wall_clearance) {
    a = equator_radius;
    b = r_inner - wall_clearance;

    rotate_extrude($fn = 200)
        polygon(
            concat(
                [[0, -b]],
                [
                    for (z = [-b : 1 : b])
                        [ a * sqrt(max(0, 1 - (z * z) / (b * b))), z ]
                ],
                [[0, b]]
            )
        );
}

// =====================================================
// Split helpers
// =====================================================

module split_top() {
    intersection() {
        children();
        translate([0, 0, R / 2 + split_gap / 2])
            cube([2 * R, 2 * R, R], center = true);
    }
}

module split_bottom() {
    intersection() {
        children();
        translate([0, 0, -R / 2 - split_gap / 2])
            cube([2 * R, 2 * R, R], center = true);
    }
}

// =====================================================
// Final assembly
// =====================================================

module full_sphere() {
    difference() {
        sphere_shell();
        holes_fibonacci();
        magnet_pockets();

        if (show_numbers)
            hole_numbers();
    }

    if (show_payload)
        color([1, 0, 0, 0.25])
            payload_ellipsoid(payload_equator_radius, payload_clearance);
}

if (show_part == "top")
    split_top() full_sphere();
else if (show_part == "bottom")
    split_bottom() full_sphere();
else
    full_sphere();
