# heat_cabin_class.py 
# 计算座舱的热负荷
def rho_air_func(t):
    """计算给定温度下的空气密度。"""
    t_k = t + 273.15
    p = 101325
    R_air = 287.05
    return p / (R_air * t_k)

class CabinHeatCalculator:
    def __init__(self, N_passengers, v_air_internal_mps, A_body, R_body,
                 A_glass, R_glass, SHGC, A_glass_sun, W_out_summer, W_in_target,
                 fraction_fresh_air, cp_air=1005, h_fg=2.45e6,
                 Q_powertrain=50, Q_electronics=100, q_person=100):
        self.N_passengers = N_passengers
        self.v_air_internal_mps = v_air_internal_mps # 座舱内部等效空气流速
        self.A_body = A_body
        self.R_body = R_body
        self.A_glass = A_glass
        self.R_glass = R_glass
        self.SHGC = SHGC
        self.A_glass_sun = A_glass_sun
        self.W_out_summer = W_out_summer
        self.W_in_target = W_in_target
        self.fraction_fresh_air = fraction_fresh_air
        self.cp_air = cp_air
        self.h_fg = h_fg
        self.Q_powertrain_invasion = Q_powertrain # 来自驾驶舱外部动力总成的热入侵
        self.Q_electronics = Q_electronics
        self.q_person = q_person

    # Private helper methods
    def _calculate_h_out(self, v_vehicle_kmh):
        """计算车身外表面对流换热系数"""
        if v_vehicle_kmh < 0: v_vehicle_kmh = 0
        v_mps = v_vehicle_kmh / 3.6
        return 5.7 + 3.8 * v_mps

    def _calculate_h_in(self): # 使用 self.v_air_internal_mps
        """计算座舱内表面对流换热系数"""
        h_natural = 2.5
        h_forced_factor = 5.5
        # 使用构造时传入的座舱内部等效空气流速
        return max(h_natural, h_natural + h_forced_factor * self.v_air_internal_mps)

    def _calculate_u_value(self, h_internal, R_material, h_external):
        """计算总传热系数 U 值"""
        if h_internal <= 0 or h_external <= 0: return 0
        R_in = 1.0 / h_internal
        R_out = 1.0 / h_external
        R_total = R_in + R_material + R_out
        if R_total <= 0: return float('inf')
        return 1.0 / R_total

    # Public methods to get heat components
    def get_internal_heat_sources(self):
        """计算座舱内部通用热源 (人，电子设备，动力总成侵入)"""
        Q_passengers_total = self.N_passengers * self.q_person
        return Q_passengers_total + self.Q_electronics + self.Q_powertrain_invasion

    def get_body_conduction_heat(self, T_outside, T_inside, v_vehicle_kmh):
        """计算通过车身(非玻璃)的传导热量"""
        h_outside = self._calculate_h_out(v_vehicle_kmh)
        h_inside = self._calculate_h_in() # 内部换热系数现在不依赖外部传入参数
        U_body = self._calculate_u_value(h_inside, self.R_body, h_outside)
        return U_body * self.A_body * (T_outside - T_inside)

    def get_glass_heat_transfer(self, T_outside, T_inside, I_solar, v_vehicle_kmh):
        """计算通过玻璃的传导和太阳辐射热量"""
        h_outside = self._calculate_h_out(v_vehicle_kmh)
        h_inside = self._calculate_h_in() # 内部换热系数
        U_glass = self._calculate_u_value(h_inside, self.R_glass, h_outside)
        Q_glass_conduction = U_glass * self.A_glass * (T_outside - T_inside)
        Q_glass_solar_gain = self.SHGC * self.A_glass_sun * I_solar
        return Q_glass_conduction + Q_glass_solar_gain

    def get_ventilation_heat_load(self, T_outside, T_inside):
        """计算夏季通风带来的热负荷 (显热+潜热)"""
        air_density_outside = rho_air_func(T_outside) # 调用模块级函数
        air_vol_flow_per_person = 0.007  # m^3/s per person
        air_vol_flow_total_demand = air_vol_flow_per_person * self.N_passengers
        air_vol_flow_fresh = air_vol_flow_total_demand * self.fraction_fresh_air
        m_air_flow_fresh = air_density_outside * air_vol_flow_fresh

        Q_vent_sensible = m_air_flow_fresh * self.cp_air * (T_outside - T_inside)
        # W_outside 和 W_inside 分别代表外部空气湿度和座舱目标湿度，已在 __init__ 中存储
        Q_vent_latent = m_air_flow_fresh * self.h_fg * max(0, self.W_out_summer - self.W_in_target)
        return Q_vent_sensible + Q_vent_latent

    def calculate_total_cabin_heat_load(self, T_outside, T_inside, v_vehicle_kmh, I_solar):
        """
        计算总的座舱热负荷。
        参数:
            T_outside (float): 车外环境温度 (°C)
            T_inside (float): 座舱内部温度 (°C)
            v_vehicle_kmh (float): 当前车速 (km/h)
            I_solar (float): 太阳辐射强度 (W/m^2)
        返回:
            float: 总座舱热负荷 (W)
        """
        Q_internal = self.get_internal_heat_sources()
        Q_body = self.get_body_conduction_heat(T_outside, T_inside, v_vehicle_kmh)
        Q_glass = self.get_glass_heat_transfer(T_outside, T_inside, I_solar, v_vehicle_kmh)
        Q_vent = self.get_ventilation_heat_load(T_outside, T_inside)

        total_load = Q_internal + Q_body + Q_glass + Q_vent
        return total_load
