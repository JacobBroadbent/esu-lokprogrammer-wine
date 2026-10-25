using System;using System.IO;using System.Threading;using System.ComponentModel;using System.IO.Ports;using System.Reflection;using System.Runtime.InteropServices;using HarmonyLib;using Microsoft.Win32.SafeHandles;
public static class SerialTimeoutCompat {
 [StructLayout(LayoutKind.Sequential)]struct Timeouts{public uint interval,multiplier,constant,writeMultiplier,writeConstant;}
 [DllImport("kernel32.dll",SetLastError=true)]static extern bool GetCommTimeouts(SafeFileHandle h,out Timeouts timeouts);
 [DllImport("kernel32.dll",SetLastError=true)]static extern bool SetCommTimeouts(SafeFileHandle h,ref Timeouts timeouts);
 public static void Apply(SerialPort __instance){
  var p=__instance;
  if(!p.IsOpen || !p.PortName.Equals("COM1",StringComparison.OrdinalIgnoreCase) || p.ReadTimeout<=0)return;
  var stream=p.BaseStream;
  var field=stream.GetType().GetField("_handle",BindingFlags.Instance|BindingFlags.NonPublic);
  if(field==null)throw new NotSupportedException("Serial timeout helper requires the tested .NET Framework SerialStream implementation.");
  var h=(SafeFileHandle)field.GetValue(stream);Timeouts t;
  if(!GetCommTimeouts(h,out t))throw new Win32Exception();
  // Wine fails to complete the MAXDWORD timeout mode used by .NET.
  // Preserve the total deadline; BeforeRead limits the request to available bytes.
  // Keep native write settings unchanged.
  t.interval=0;t.multiplier=0;t.constant=(uint)p.ReadTimeout;
  if(!SetCommTimeouts(h,ref t))throw new Win32Exception();
 }
 static void Log(string value){var path=Environment.GetEnvironmentVariable("LOKPROGRAMMER_SERIAL_LOG");if(String.IsNullOrEmpty(path))return;try{File.AppendAllText(path,DateTime.Now.ToString("o")+" T"+Thread.CurrentThread.ManagedThreadId+" "+value+Environment.NewLine);}catch{}}
 public static void BeforeRead(SerialPort __instance,byte[] buffer,int offset,ref int count){
  var p=__instance;
  // Keep ordinary validation, non-COM1 ports and zero/infinite timeout behavior.
  if(!p.IsOpen || buffer==null || offset<0 || count<=0 || offset>buffer.Length-count || !p.PortName.Equals("COM1",StringComparison.OrdinalIgnoreCase) || p.ReadTimeout<=0)return;
  var stream=p.BaseStream;
  var h=(SafeFileHandle)stream.GetType().GetField("_handle",BindingFlags.Instance|BindingFlags.NonPublic).GetValue(stream);Timeouts t;
  if(!GetCommTimeouts(h,out t))throw new Win32Exception();
  int requested=count,deadline=p.ReadTimeout;
  Log("READ enter count="+count+" baud="+p.BaudRate+" managedTimeout="+deadline+" native="+t.interval+","+t.multiplier+","+t.constant);
  Apply(p);
  var timer=System.Diagnostics.Stopwatch.StartNew();
  while(true){
   int available=p.BytesToRead;
   if(available>0){
    // SerialPort.Read may return fewer bytes than requested. Ask the original
    // method only for bytes already buffered, so Wine need not wait for 8192.
    count=Math.Min(requested,available);
    Log("READ ready available="+available+" readCount="+count+" waitMs="+timer.ElapsedMilliseconds);
    return;
   }
   if(timer.ElapsedMilliseconds>=deadline)throw new TimeoutException("The operation has timed out.");
   Thread.Sleep(1);
  }
 }
 public static void AfterRead(int __result){Log("READ return bytes="+__result);}
 public static Exception ReadError(Exception __exception){if(__exception!=null)Log("READ exception "+__exception.GetType().FullName+": "+__exception.Message);return __exception;}
 public static void Install(){
  var h=new Harmony("local.lokprogrammer.wine.serial-timeout");
  var after=new HarmonyMethod(typeof(SerialTimeoutCompat).GetMethod("Apply"));
  foreach(var name in new[]{"Open","set_ReadTimeout","set_WriteTimeout"})
   h.Patch(typeof(SerialPort).GetMethod(name,BindingFlags.Public|BindingFlags.Instance),postfix:after);
  h.Patch(typeof(SerialPort).GetMethod("Read",new[]{typeof(byte[]),typeof(int),typeof(int)}),prefix:new HarmonyMethod(typeof(SerialTimeoutCompat).GetMethod("BeforeRead")),postfix:new HarmonyMethod(typeof(SerialTimeoutCompat).GetMethod("AfterRead")),finalizer:new HarmonyMethod(typeof(SerialTimeoutCompat).GetMethod("ReadError")));
 }
}
