#ifdef GL_ES
precision highp float;
#endif

uniform sampler2D texture0;
uniform vec2 resolution;

void main() {
    vec2 uv = gl_FragCoord.xy / resolution.xy;
    vec4 color = vec4(0.0);
    
    float offset = 1.0 / 300.0;  // Adjust the blur amount by changing the divisor

    for (float x = -4.0; x <= 4.0; x += 2.0) {
        for (float y = -4.0; y <= 4.0; y += 2.0) {
            vec2 sample = uv + vec2(x * offset, y * offset);
            color += texture2D(texture0, sample);
        }
    }

    color /= 81.0;
    gl_FragColor = color;
}
