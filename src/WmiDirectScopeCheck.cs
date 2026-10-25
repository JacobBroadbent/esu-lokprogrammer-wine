using System;
using System.Management;
using System.Reflection;
using System.Runtime.InteropServices;
[assembly: System.Runtime.Versioning.TargetFramework(".NETFramework,Version=v4.8")]
public class DirectWmi {
 [DllImport("ole32.dll")]static extern int CoCreateInstance(ref Guid clsid,IntPtr outer,uint context,ref Guid iid,out IntPtr result);
 [UnmanagedFunctionPointer(CallingConvention.StdCall)]delegate int ConnectServer(IntPtr self,[MarshalAs(UnmanagedType.BStr)]string path,[MarshalAs(UnmanagedType.BStr)]string user,[MarshalAs(UnmanagedType.BStr)]string password,[MarshalAs(UnmanagedType.BStr)]string locale,int flags,[MarshalAs(UnmanagedType.BStr)]string authority,IntPtr context,out IntPtr services);
 public static void Connect(ManagementScope scope){
  if((!String.IsNullOrEmpty(scope.Path.Server) && scope.Path.Server!="." && !scope.Path.Server.Equals(Environment.MachineName,StringComparison.OrdinalIgnoreCase)) || !String.IsNullOrEmpty(scope.Options.Username))throw new NotSupportedException("Only local WMI is supported by this diagnostic.");
  Guid clsid=new Guid("4590f811-1d3a-11d0-891f-00aa004b2e24"),iid=new Guid("dc12a687-737f-11cf-884d-00aa004b2e24");
  IntPtr locator=IntPtr.Zero,services=IntPtr.Zero;
  try {
   Marshal.ThrowExceptionForHR(CoCreateInstance(ref clsid,IntPtr.Zero,1,ref iid,out locator));
   var method=Marshal.GetDelegateForFunctionPointer(Marshal.ReadIntPtr(Marshal.ReadIntPtr(locator),3*IntPtr.Size),typeof(ConnectServer)) as ConnectServer;
   Marshal.ThrowExceptionForHR(method(locator,scope.Path.Path,null,null,null,0,null,IntPtr.Zero,out services));
   var type=typeof(ManagementScope).Assembly.GetType("System.Management.IWbemServices",true);
   var proxy=Marshal.GetTypedObjectForIUnknown(services,type);
   typeof(ManagementScope).GetField("wbemServices",BindingFlags.Instance|BindingFlags.NonPublic).SetValue(scope,proxy);
  }finally{if(services!=IntPtr.Zero)Marshal.Release(services);if(locator!=IntPtr.Zero)Marshal.Release(locator);}
 }
 [STAThread]static int Main(){try{
  var scope=new ManagementScope(@"\\.\root\CIMV2");Connect(scope);
  using(var s=new ManagementObjectSearcher(scope,new ObjectQuery("SELECT * FROM Win32_OperatingSystem")))using(var rows=s.Get())Console.WriteLine("Direct local WMI: "+rows.Count+" rows");
  return 0;
 }catch(Exception e){Console.WriteLine(e);return 1;}}
}
