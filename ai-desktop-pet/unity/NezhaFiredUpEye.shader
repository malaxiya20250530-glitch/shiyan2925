Shader "Nezha/EyeFiredUp"
{
    Properties
    {
        _BaseColor ("瞳色", Color) = (0.05, 0.03, 0.02, 1)
        _IrisTex ("虹膜纹理", 2D) = "white" {}
        
        [Header("FiredUp 燃烧")]
        _FiredUp ("燃烧强度", Range(0, 1)) = 0
        _BurnColor ("燃烧色", Color) = (1, 0.3, 0, 1)
        _BurnGlow ("燃烧光晕", Range(0, 5)) = 2
        _BurnEdge ("边缘烧灼宽度", Range(0, 0.5)) = 0.1
        
        [Header("动态扰动")]
        _NoiseSpeed ("扰动速度", Range(0, 10)) = 3
        _NoiseScale ("扰动强度", Range(0, 0.5)) = 0.1
        
        [Header("瞳孔")]
        _PupilSize ("瞳孔大小", Range(0, 1)) = 0.3
        _PupilColor ("瞳孔色", Color) = (0, 0, 0, 1)
        
        [Header("高光")]
        _HighlightPos ("高光位置", Vector) = (0.3, 0.2, 0, 0)
        _HighlightSize ("高光大小", Range(0, 0.3)) = 0.05
        _HighlightColor ("高光色", Color) = (1, 1, 1, 1)
    }

    SubShader
    {
        Tags { "RenderType" = "Transparent" "Queue" = "Transparent" }
        Blend SrcAlpha OneMinusSrcAlpha
        Cull Off

        Pass
        {
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #include "UnityCG.cginc"

            struct appdata
            {
                float4 vertex : POSITION;
                float2 uv : TEXCOORD0;
                float3 normal : NORMAL;
            };

            struct v2f
            {
                float2 uv : TEXCOORD0;
                float3 normal : TEXCOORD1;
                float3 viewDir : TEXCOORD2;
                float4 vertex : SV_POSITION;
            };

            sampler2D _IrisTex;
            float4 _IrisTex_ST;

            float4 _BaseColor;
            float4 _BurnColor;
            float _FiredUp;
            float _BurnGlow;
            float _BurnEdge;
            float _NoiseSpeed;
            float _NoiseScale;
            float _PupilSize;
            float4 _PupilColor;
            float4 _HighlightPos;
            float _HighlightSize;
            float4 _HighlightColor;

            // 简易噪声函数
            float hash(float2 p)
            {
                return frac(sin(dot(p, float2(127.1, 311.7))) * 43758.5453);
            }

            float noise(float2 p)
            {
                float2 i = floor(p);
                float2 f = frac(p);
                f = f * f * (3.0 - 2.0 * f);
                return lerp(
                    lerp(hash(i), hash(i + float2(1, 0)), f.x),
                    lerp(hash(i + float2(0, 1)), hash(i + float2(1, 1)), f.x),
                    f.y
                );
            }

            v2f vert(appdata v)
            {
                v2f o;
                o.vertex = UnityObjectToClipPos(v.vertex);
                o.uv = TRANSFORM_TEX(v.uv, _IrisTex);
                o.normal = UnityObjectToWorldNormal(v.normal);
                float3 worldPos = mul(unity_ObjectToWorld, v.vertex).xyz;
                o.viewDir = normalize(_WorldSpaceCameraPos - worldPos);
                return o;
            }

            fixed4 frag(v2f i) : SV_Target
            {
                float2 uv = i.uv - 0.5; // 居中

                // ── 瞳孔 ──
                float pupilDist = length(uv);
                float pupil = smoothstep(_PupilSize, _PupilSize * 1.2, pupilDist);

                // ── 虹膜纹理 ──
                float irisAngle = atan2(uv.y, uv.x);
                float2 irisUV = float2(irisAngle / (2 * 3.14159) + 0.5, pupilDist * 2);
                fixed4 iris = tex2D(_IrisTex, irisUV);

                // ── FiredUp 火焰扰动 ──
                float burn = _FiredUp;
                float n = noise(uv * 10 + _Time.y * _NoiseSpeed);
                float burnPattern = smoothstep(burn - _BurnEdge, burn + _BurnEdge,
                    pupilDist + n * _NoiseScale * burn);

                // ── 颜色混合 ──
                float3 baseCol = _BaseColor.rgb;
                float3 burnCol = _BurnColor.rgb * (1 + _BurnGlow * burnPattern);
                float3 col = lerp(baseCol, burnCol, burnPattern * burn);

                // ── 瞳孔 → 燃烧时收缩 ──
                float pupilMask = lerp(pupil, 1, burn * 0.7);
                col = lerp(_PupilColor.rgb, col, pupilMask);

                // ── 高光 ──
                float2 hl = float2(_HighlightPos.x, _HighlightPos.y);
                float highlight = smoothstep(_HighlightSize, 0,
                    length(uv - hl)) * pupilMask;
                col += _HighlightColor.rgb * highlight * 0.5;

                // ── 边缘菲涅尔光（燃烧时增强） ──
                float fresnel = 1 - abs(dot(i.normal, i.viewDir));
                fresnel = pow(fresnel, 3);
                col += burnCol * fresnel * burn * 0.3;

                // ── 自发光（燃烧时） ──
                float emission = burnPattern * burn * (_BurnGlow * 0.5);

                return fixed4(col + emission, 1);
            }
            ENDCG
        }
    }
    FallBack "Diffuse"
}
