using UnityEngine;

/// <summary>
/// 哪吒风火轮 — 双脚双轮青焰粒子系统
/// 常驻旋转 + fired_up 时火焰爆发 + 拖尾
/// </summary>
public class NezhaFireWheels : MonoBehaviour
{
    [Header("轮盘")]
    public GameObject leftWheel;   // 左脚轮盘模型（挂载点）
    public GameObject rightWheel;  // 右脚轮盘模型
    public float spinSpeed = 720f; // 每秒旋转角度

    [Header("火焰粒子")]
    public ParticleSystem leftFlame;
    public ParticleSystem rightFlame;
    public ParticleSystem burstFlame; // fired_up 爆发粒子
    [ColorUsage(true, true)]
    public Color normalFlameColor = new Color(0f, 0.8f, 1f, 1f);   // 青焰
    [ColorUsage(true, true)]
    public Color firedUpFlameColor = new Color(1f, 0.3f, 0f, 1f);  // 赤焰

    [Header("拖尾")]
    public TrailRenderer leftTrail;
    public TrailRenderer rightTrail;

    [Header("参数")]
    public float normalEmissionRate = 80f;
    public float firedUpEmissionRate = 300f;
    public float normalFlameSize = 0.15f;
    public float firedUpFlameSize = 0.4f;
    public float burstDuration = 0.6f;

    private bool _isFiredUp;
    private float _burstTimer;

    void Start()
    {
        // 自动查找骨骼挂载点
        if (leftWheel == null)  leftWheel  = FindBone("LeftFoot");
        if (rightWheel == null) rightWheel = FindBone("RightFoot");

        // 没有粒子系统则自动创建
        if (leftFlame == null)  leftFlame  = CreateFlamePS(leftWheel,  "LeftFlame");
        if (rightFlame == null) rightFlame = CreateFlamePS(rightWheel, "RightFlame");

        SetFlameState(false);
    }

    void Update()
    {
        // 轮盘旋转
        float spin = spinSpeed * Time.deltaTime;
        if (leftWheel != null)  leftWheel.transform.Rotate(Vector3.right, spin);
        if (rightWheel != null) rightWheel.transform.Rotate(Vector3.right, spin);

        // 爆发计时
        if (_burstTimer > 0f)
        {
            _burstTimer -= Time.deltaTime;
            if (_burstTimer <= 0f && burstFlame != null)
                burstFlame.Stop();
        }
    }

    /// <summary>切换 fired_up 状态</summary>
    public void SetFiredUp(bool active)
    {
        _isFiredUp = active;
        SetFlameState(active);

        if (active && burstFlame != null)
        {
            burstFlame.Play();
            _burstTimer = burstDuration;
        }
    }

    void SetFlameState(bool firedUp)
    {
        var col = firedUp ? firedUpFlameColor : normalFlameColor;
        var emission = firedUp ? firedUpEmissionRate : normalEmissionRate;
        var size = firedUp ? firedUpFlameSize : normalFlameSize;

        foreach (var ps in new[] { leftFlame, rightFlame })
        {
            if (ps == null) continue;
            var main = ps.main;
            main.startColor = col;
            main.startSize = size;

            var em = ps.emission;
            em.rateOverTime = emission;

            // fired_up 时扩大火焰范围
            var shape = ps.shape;
            shape.radius = firedUp ? 0.25f : 0.1f;
        }

        // 拖尾颜色
        foreach (var tr in new[] { leftTrail, rightTrail })
        {
            if (tr == null) continue;
            tr.startColor = col;
            tr.time = firedUp ? 0.5f : 0.15f;
        }
    }

    GameObject FindBone(string boneName)
    {
        foreach (var t in GetComponentsInChildren<Transform>())
            if (t.name == boneName) return t.gameObject;
        return null;
    }

    ParticleSystem CreateFlamePS(GameObject parent, string name)
    {
        if (parent == null) return null;

        var go = new GameObject(name);
        go.transform.SetParent(parent.transform, false);
        go.transform.localPosition = Vector3.zero;

        var ps = go.AddComponent<ParticleSystem>();
        var main = ps.main;
        main.startLifetime = new ParticleSystem.MinMaxCurve(0.2f, 0.6f);
        main.startSpeed = new ParticleSystem.MinMaxCurve(0.5f, 2f);
        main.startSize = normalFlameSize;
        main.startColor = normalFlameColor;
        main.simulationSpace = ParticleSystemSimulationSpace.Local;
        main.loop = true;

        var em = ps.emission;
        em.rateOverTime = normalEmissionRate;

        var shape = ps.shape;
        shape.shapeType = ParticleSystemShapeType.Circle;
        shape.radius = 0.1f;

        var sizeOverLifetime = ps.sizeOverLifetime;
        sizeOverLifetime.enabled = true;
        sizeOverLifetime.size = new ParticleSystem.MinMaxCurve(1f,
            new AnimationCurve(new Keyframe(0, 1), new Keyframe(1, 0)));

        // 如果没有材质则跳过（Unity 会用默认粒子材质）
        var renderer = ps.GetComponent<ParticleSystemRenderer>();
        renderer.renderMode = ParticleSystemRenderMode.Billboard;

        return ps;
    }
}
