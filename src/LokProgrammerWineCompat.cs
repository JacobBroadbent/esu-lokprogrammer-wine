using System;
using System.IO;
using System.Management;
using System.Reflection;
using System.Threading;
using HarmonyLib;
[assembly: AssemblyVersion("5.2.18.26120")]
public class LokProgrammerWineCompat {
 static void Log(string s){try{File.AppendAllText(Environment.GetEnvironmentVariable("LOKPROGRAMMER_DIAGNOSTIC_LOG")??Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"LokProgrammerWineCompat.log"),DateTime.Now.ToString("o")+" "+s+Environment.NewLine);}catch{}}
 public static void Prepare(ManagementObjectSearcher __instance){
  Log("Local WMI connection on "+Thread.CurrentThread.GetApartmentState()+"; query="+__instance.Query.QueryString);
  DirectWmi.Connect(__instance.Scope);
 }
 public static void Install(string[] unused){
  new Harmony("local.lokprogrammer.wine.direct-wmi").Patch(typeof(ManagementObjectSearcher).GetMethod("Get",Type.EmptyTypes),prefix:new HarmonyMethod(typeof(LokProgrammerWineCompat).GetMethod("Prepare")));
  SerialTimeoutCompat.Install();
  Log("Installed local WMI and finite serial-read timeout compatibility helpers.");
 }
 public static void CheckWmi(){
  try{
   foreach(var q in new[]{"SELECT * FROM Win32_OperatingSystem","SELECT Service FROM Win32_PnpEntity WHERE Caption LIKE '%(COM1%'"})
   using(var searcher=new ManagementObjectSearcher(@"\\.\root\CIMV2",q))using(var rows=searcher.Get())
    Console.WriteLine("WMI check: "+q+"; rows="+rows.Count);
   AppDomain.CurrentDomain.SetData("CheckExitCode",0);
  }catch(Exception e){Console.Error.WriteLine(e);AppDomain.CurrentDomain.SetData("CheckExitCode",1);}
 }
 [STAThread]public static int Main(string[] args){
  if(args.Length>0 && args[0]=="--version"){Console.WriteLine("LokProgrammerWineCompat repository build 0.1.0");return 0;}
  if(args.Length>0 && args[0]=="--check-wmi"){
   var here=Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location);
   var settings=new AppDomainSetup{ApplicationBase=here,AppDomainInitializer=Install};
   if(File.Exists(Path.Combine(here,"LokProgrammer.exe.config")))settings.ConfigurationFile=Path.Combine(here,"LokProgrammer.exe.config");
   var check=AppDomain.CreateDomain("Compatibility loader and WMI check",null,settings);
   check.DoCallBack(CheckWmi);
   return (int)check.GetData("CheckExitCode");
  }
  if(args.Length>0 && args[0]=="--self-test"){
   try{
    Install(new string[0]);
    foreach(var q in new[]{"SELECT * FROM Win32_OperatingSystem","SELECT Service FROM Win32_PnpEntity WHERE Caption LIKE '%(COM1%'"})
    using(var s=new ManagementObjectSearcher(@"\\.\root\CIMV2",q))using(var rows=s.Get()){
     Console.WriteLine("Real WMI query: "+q+"; rows="+rows.Count);
     foreach(ManagementObject row in rows)Console.WriteLine("Actual object: "+row.Path.Path);
    }
    using(var p=new System.IO.Ports.SerialPort("COM1",921600)){
     p.Handshake=System.IO.Ports.Handshake.RequestToSend;p.ReadTimeout=200;p.WriteTimeout=200;p.Open();
     var zeroTimer=System.Diagnostics.Stopwatch.StartNew();
     if(p.Read(new byte[0],0,0)!=0 || zeroTimer.ElapsedMilliseconds>100)throw new Exception("Zero-count read must return immediately.");
     Console.WriteLine("Zero-count read returned immediately.");
     var timer=System.Diagnostics.Stopwatch.StartNew();
     try{Console.WriteLine("Read returned "+p.Read(new byte[10],0,10)+" bytes");}
     catch(TimeoutException){Console.WriteLine("Finite read timed out after "+timer.ElapsedMilliseconds+" ms; no data sent.");if(timer.ElapsedMilliseconds<150 || timer.ElapsedMilliseconds>2000)return 2;}
    }
    return 0;
   }catch(Exception e){Console.WriteLine(e);return 1;}
  }
  var app=Path.Combine(Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location),"LokProgrammer.exe");
  var setup=new AppDomainSetup{ApplicationBase=Path.GetDirectoryName(app),ConfigurationFile=app+".config",AppDomainInitializer=Install};
  var domain=AppDomain.CreateDomain("LokProgrammer local WMI compatibility",null,setup);
  return domain.ExecuteAssembly(app,new string[0]);
 }
}
