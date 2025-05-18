# heat_vehicle.py
# 该模块包含用于计算车辆基本物理特性相关的函数，
# 此程序默认输入数值合法。
class PowerHeatCalculator:
    def __init__(self,m,motor_eta,u_batt, r_int, eta_inv):
        self.m = m #车辆质量
        self.motor_eta = motor_eta#
        self.u_batt = u_batt
        self.r_int = r_int
        self.eta_inv = eta_inv
    #private
    @staticmethod
    def _rho_air_func(T_amb):
        """计算给定温度下的空气密度。
        参数:
        t: 环境温度 (°C)。
        返回:
        空气密度 (kg/m^3)。
        """
        t_k = T_amb + 273.15# 开尔文 = 摄氏度 + 273.15
        p = 101325# 标准大气压 (单位: 帕斯卡 Pa)
        R_air = 287.05# 空气的比气体常数 (单位: 焦耳/(千克·开尔文) J/(kg·K))
        return p / (R_air * t_k)# 根据理想气体状态方程 rho = p / (R * T) 计算空气密度

    def _F_roll_func(self):
        mu = 0.008# 滚动阻力系数 (无量纲)
        m =  self.m
        g = 9.8# 重力加速度 (单位: 米/平方秒 m/s^2)
        f = mu * m * g#滚动摩擦力
        return f
    def _F_aero_func(self,v_kmh,T_amb):
        const = 0.5
        rho = PowerHeatCalculator._rho_air_func(T_amb)
        Cd = 0.22# 空气阻力系数 (无量纲)，取决于车辆外形设计
        a = 3.00# 车辆的迎风面积 (m^2)
        vmps = v_kmh / 3.6#速度转化
        f_air = const * rho * Cd * a * (vmps**2)#空气阻力
        return f_air
    '''
    public
    '''
    
    def P_wheel_func(self,v_kmh,T_amb):#车辆功率
        v_mps = v_kmh  / 3.6
        force_roll = self._F_roll_func() #计算滚动阻力( N)
        force_aero = self._F_aero_func(v_kmh,T_amb)#计算空气阻力 (N)
        force_total = force_aero + force_roll#总行驶阻力 (不考虑坡度阻力及加速阻力)(单位: N)
        return force_total * v_mps# 功率(W) P = F * v (力乘以速度)
    def P_motor_func(self,v_kmh,T_amb):#电机功率
        p_motor_in = self.P_wheel_func(v_kmh,T_amb)/self.motor_eta
        return p_motor_in
    
    
    def P_inv_fuc(self,v_kmh, T_amb):
        p_motor_in = self.P_motor_func(v_kmh, T_amb) # 这是电机的输入功率，也是逆变器的输出功率
        return p_motor_in
    def Q_mot_func(self,v_kmh,T_amb):#电机产热
        p_motor = self.P_motor_func(v_kmh,T_amb)
        Q_mot = p_motor * (1 - self.motor_eta)
        return Q_mot
    def Q_inv_func(self,v_kmh,T_amb):#逆变器
        p_motor = self.P_motor_func(v_kmh,T_amb)
        Q_inv = p_motor * (1 - self.eta_inv) / self.eta_inv
        return Q_inv
    def Q_batt_func(self,p_motor):#电池
        I_batt = p_motor / self.u_batt
        Q_heat_batt = (I_batt**2) * self.r_int
        return Q_heat_batt