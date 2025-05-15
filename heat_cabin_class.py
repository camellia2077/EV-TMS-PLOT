# heat_cabin_class.py
# 计算各部件和座舱温度变化率

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
                 Q_powertrain=50, Q_electronics=100, q_person=80):
        """
        初始化座舱热负荷计算器。
        参数:
            N_passengers (int): 乘客人数
            v_air_in_mps (float): 新风速度 (m/s) - 或内部空气等效速度
            A_body (float): 车身面积 (m^2)
            R_body (float): 车身热阻 (m^2·K/W)
            A_glass (float): 玻璃面积 (m^2)
            R_glass (float): 玻璃热阻 (m^2·K/W)
            SHGC (float): 太阳得热系数
            A_glass_sun (float): 玻璃受太阳辐射有效面积 (m^2)
            W_out_summer (float): 夏季车外空气湿度 (kg_water/kg_air)
            W_in_target (float): 座舱目标湿度 (kg_water/kg_air)
            fraction_fresh_air (float): 新风比例 (百分比)
            cp_air (float): 空气比热容 (J/kg·K)
            h_fg (float): 水的汽化潜热 (J/kg)
            q_person (float): 每位乘客产热 (W)
            q_electronics (float): 电子设备产热 (W)
            q_powertrain (float): 动力总成侵入热 (W)
        """
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

    # Private
    def _calculate_h_out(self, v_vehicle_kmh):
        """计算车身外表面对流换热系数"""
        v_mps = v_vehicle_kmh / 3.6
        return 5.7 + 3.8 * v_mps

    def _calculate_h_in(self):
        """计算座舱内表面对流换热系数"""
        h_natural = 2.5
        h_forced_factor = 5.5
        return max(h_natural, h_natural + h_forced_factor * self.v_air_internal_mps)

    def _calculate_u_value(self, h_internal, R_material, h_external):
        """计算总传热系数 U 值"""
        R_in = 1.0 / h_internal
        R_out = 1.0 / h_external
        R_total = R_in + R_material + R_out
        return 1.0 / R_total

    # Public methods to get heat components
    def get_internal_heat_sources(self):
        """计算座舱内部通用热源 (人，电子设备，动力总成侵入)"""
        Q_passengers_total = self.N_passengers * self.q_person#所有乘客散发热量(W)
        Q_internal_total = Q_passengers_total + self.Q_electronics + self.Q_powertrain_invasion#(乘客，内部电器，动力系统)向座舱发热量(W)
        return Q_internal_total

    def get_body_conduction_heat(self, T_outside, T_inside, v_vehicle_kmh):
        """计算通过车身(非玻璃)的传导热量"""
        h_outside = self._calculate_h_out(v_vehicle_kmh)# 计算车辆外表面换热系数(W/(m^2·K))
        h_inside = self._calculate_h_in() # 计算车辆内部换热系数(W/(m^2·K))
        U_body = self._calculate_u_value(h_inside, self.R_body, h_outside)# 计算总传热系数(W/(m^2·K))
        return U_body * self.A_body * (T_outside - T_inside)

    def get_glass_heat_transfer(self, T_outside, T_inside, I_solar, v_vehicle_kmh):
        """计算通过玻璃的传导和太阳辐射热量"""
        h_outside = self._calculate_h_out(v_vehicle_kmh)# 外部换热系数(W/(m^2·K))
        h_inside = self._calculate_h_in() # 内部换热系数(W/(m^2·K))
        U_glass = self._calculate_u_value(h_inside, self.R_glass, h_outside)# 玻璃总换热系数(W/(m^2·K))
        Q_glass_conduction = U_glass * self.A_glass * (T_outside - T_inside)# 环境通对璃传入的热量(W)
        Q_glass_solar_gain = self.SHGC * self.A_glass_sun * I_solar# 通过太阳辐射对玻璃传导的热量(W)
        return Q_glass_conduction + Q_glass_solar_gain

    def get_ventilation_heat_load(self, T_outside, T_inside):
        """计算夏季通风带来的热负荷 (显热+潜热)"""
        """
        计算总的座舱热负荷。
        参数:
            T_outside (float): 车外环境温度 (°C)
            T_inside (float): 座舱内部温度 (°C)
        返回:
            float: 新风热负荷 (W)
        """
        air_density_outside = rho_air_func(T_outside) # 计算外部环境空气密度(kg/m^3)
        air_vol_flow_per_person = 0.007 #每名乘客需要的新风量 (m^3/s)
        air_vol_flow_total_demand = air_vol_flow_per_person * self.N_passengers #所有乘客需要的新风量(m^3/s)
        air_vol_flow_fresh = air_vol_flow_total_demand * self.fraction_fresh_air
        m_air_flow_fresh = air_density_outside * air_vol_flow_fresh #所需空气质量(kg)

        Q_vent_sensible = m_air_flow_fresh * self.cp_air * (T_outside - T_inside)# 显热负荷(W)
        # W_outside 和 W_inside 分别代表外部空气湿度和座舱目标湿度，已在 __init__ 中存储
        Q_vent_latent = m_air_flow_fresh * self.h_fg * max(0, self.W_out_summer - self.W_in_target)# 潜热负荷
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
        Q_internal = self.get_internal_heat_sources() # 内部热负荷
        Q_body = self.get_body_conduction_heat(T_outside, T_inside, v_vehicle_kmh) # 环境传入车身热负荷
        Q_glass = self.get_glass_heat_transfer(T_outside, T_inside, I_solar, v_vehicle_kmh) # 玻璃热负荷(包括环境与太阳辐射)
        Q_vent = self.get_ventilation_heat_load(T_outside, T_inside) #新风负荷

        total_load = Q_internal + Q_body + Q_glass + Q_vent
        return total_load